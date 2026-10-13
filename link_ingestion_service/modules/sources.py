"""Pluggable external link-data sources.

Every external system has its own HTTP contract, so the source-specific part
lives behind `BaseLinkSource` and the scheduler (polling, failure counting,
publishing) stays source-agnostic.

Connecting a new API = subclass `BaseLinkSource`, implement `fetch`, register
it in `_SOURCES`, then set `metadata.external_source.provider = "<name>"` on
the links that should be read from it.
"""
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

import httpx

from core.config import settings

logger = logging.getLogger("LinkSource")


class SourceError(Exception):
    """Raised by a source when a reading could not be obtained."""


@dataclass
class LinkConfig:
    link_id: int
    provider: str
    external_id: str
    interval: int
    name: Optional[str] = None
    feeder_id: Optional[int] = None
    allowed_current: Optional[float] = None
    field_map: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        return repr((self.provider, self.external_id, self.interval, self.allowed_current,
                     sorted(self.field_map.items()), sorted(self.options.items())))


@dataclass
class LinkReading:
    values: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _dig(data: Any, path: str) -> Any:
    """Resolve a dotted path ("data.items.0.value") inside a JSON document."""
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            # Accept both seconds and milliseconds since epoch.
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def extract_reading(document: Any, link: LinkConfig) -> LinkReading:
    """Map a JSON response to numeric fields.

    With a `field_map` ({"current": "data.i", "timestamp": "data.ts"}) only the
    mapped paths are read; without one every top-level numeric value is kept.
    """
    values: Dict[str, float] = {}
    timestamp = None

    if link.field_map:
        for name, path in link.field_map.items():
            raw = _dig(document, path)
            if name == "timestamp":
                timestamp = _parse_timestamp(raw)
                continue
            number = _to_float(raw)
            if number is not None:
                values[name] = number
    elif isinstance(document, dict):
        for name, raw in document.items():
            if name == "timestamp":
                timestamp = _parse_timestamp(raw)
                continue
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                values[name] = float(raw)

    if not values:
        raise SourceError("Response contained no numeric values for the configured fields.")
    return LinkReading(values=values, timestamp=timestamp or datetime.now(timezone.utc))


class BaseLinkSource(ABC):
    name: str = "base"

    def is_configured(self, link: LinkConfig) -> bool:
        return True

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient, link: LinkConfig) -> LinkReading:
        """Return the latest reading of `link` or raise SourceError."""


class MockLinkSource(BaseLinkSource):
    """Random values - lets the whole pipeline (RabbitMQ -> InfluxDB -> API)
    be verified before the real external API is available."""
    name = "mock"

    async def fetch(self, client: httpx.AsyncClient, link: LinkConfig) -> LinkReading:
        rated = link.allowed_current or 200.0
        current = round(random.uniform(0.2, 0.9) * rated, 2)
        return LinkReading(values={
            "current": current,
            "voltage": round(random.uniform(19_500, 20_500), 1),
            "load_percent": round(current / rated * 100, 2),
        })


class HttpJsonLinkSource(BaseLinkSource):
    """Calls LINK_API_URL_TEMPLATE.format(external_id=...) and maps the JSON body.

    Per-link `options` may override: url (URL template), method, params,
    headers, json (request body for POST).
    """
    name = "http"

    def is_configured(self, link: LinkConfig) -> bool:
        return bool(link.options.get("url") or settings.LINK_API_URL_TEMPLATE)

    def _headers(self, link: LinkConfig) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if settings.LINK_API_TOKEN:
            scheme = settings.LINK_API_AUTH_SCHEME
            headers[settings.LINK_API_AUTH_HEADER] = (
                f"{scheme} {settings.LINK_API_TOKEN}" if scheme else settings.LINK_API_TOKEN
            )
        headers.update(link.options.get("headers") or {})
        return headers

    async def fetch(self, client: httpx.AsyncClient, link: LinkConfig) -> LinkReading:
        template = link.options.get("url") or settings.LINK_API_URL_TEMPLATE
        url = template.format(external_id=link.external_id)
        method = str(link.options.get("method", "GET")).upper()

        try:
            response = await client.request(
                method, url,
                headers=self._headers(link),
                params=link.options.get("params"),
                json=link.options.get("json") if method != "GET" else None,
                timeout=settings.LINK_API_TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise SourceError(f"Request to {url} failed: {e!r}") from e

        if response.status_code >= 400:
            raise SourceError(f"{url} returned HTTP {response.status_code}: {response.text[:200]}")
        try:
            document = response.json()
        except ValueError as e:
            raise SourceError(f"{url} did not return JSON.") from e
        return extract_reading(document, link)


_SOURCES: Dict[str, Type[BaseLinkSource]] = {
    MockLinkSource.name: MockLinkSource,
    HttpJsonLinkSource.name: HttpJsonLinkSource,
}
_instances: Dict[str, BaseLinkSource] = {}


def get_source(provider: str) -> Optional[BaseLinkSource]:
    key = (provider or "").lower()
    if key not in _instances:
        source_cls = _SOURCES.get(key)
        if source_cls is None:
            return None
        _instances[key] = source_cls()
    return _instances[key]
