"""Pluggable SMS panel adapters.

Every SMS panel (Kavenegar, sms.ir, Melipayamak, Ghasedak, ...) has its own
HTTP contract, so the panel-specific part lives behind `BaseSMSGateway` and
`SMSProvider` (retry, normalization, concurrency) stays panel-agnostic.

Connecting a real panel = subclass `BaseSMSGateway`, implement `send_one`,
register it in `_GATEWAYS` and set `SMS_PROVIDER=<name>` in `.env`.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Type

import httpx

from core.config import settings

logger = logging.getLogger("SMSGateway")


@dataclass
class SMSResult:
    success: bool
    # False for errors that will never succeed on retry (bad number, invalid
    # credentials, insufficient credit) - SMSProvider stops retrying on these.
    retryable: bool = False
    provider_message_id: Optional[str] = None
    error: Optional[str] = None


class BaseSMSGateway(ABC):
    name: str = "base"

    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def send_one(self, client: httpx.AsyncClient, phone: str, text: str) -> SMSResult:
        """Send a single SMS. `phone` is already normalized (09xxxxxxxxx)."""


class LogOnlySMSGateway(BaseSMSGateway):
    """Dry-run gateway used until the real panel credentials are provided:
    nothing leaves the server, every SMS is only written to the logs so the
    whole pipeline (recipients, texts, audit logs) can be verified end to end."""
    name = "log"

    async def send_one(self, client: httpx.AsyncClient, phone: str, text: str) -> SMSResult:
        logger.info(f"📵 [DRY-RUN SMS] to={phone} | text={text!r}")
        return SMSResult(success=True, provider_message_id="dry-run")


class GenericHttpSMSGateway(BaseSMSGateway):
    """Simple JSON POST gateway: {api_key, line, to, text} -> SMS_API_URL.
    Kept as a template for panels with a plain REST API."""
    name = "http"

    def is_configured(self) -> bool:
        return bool(settings.SMS_API_URL and settings.SMS_API_KEY)

    async def send_one(self, client: httpx.AsyncClient, phone: str, text: str) -> SMSResult:
        payload = {
            "api_key": settings.SMS_API_KEY,
            "line": settings.SMS_LINE_NUMBER,
            "to": phone,
            "text": text,
        }
        try:
            response = await client.post(settings.SMS_API_URL, json=payload)
        except httpx.HTTPError as e:
            return SMSResult(success=False, retryable=True, error=str(e))

        if response.is_success:
            message_id = None
            try:
                body = response.json()
                if isinstance(body, dict):
                    message_id = str(body.get("message_id") or body.get("id") or "") or None
            except ValueError:
                pass
            return SMSResult(success=True, provider_message_id=message_id)

        # A 4xx (bad number, bad request, auth) will never succeed on retry;
        # only a 5xx / 429 from the panel is worth retrying.
        return SMSResult(
            success=False,
            retryable=response.status_code >= 500 or response.status_code == 429,
            error=f"HTTP {response.status_code}: {response.text[:300]}",
        )


_GATEWAYS: Dict[str, Type[BaseSMSGateway]] = {
    LogOnlySMSGateway.name: LogOnlySMSGateway,
    GenericHttpSMSGateway.name: GenericHttpSMSGateway,
}


def build_sms_gateway() -> BaseSMSGateway:
    name = settings.SMS_PROVIDER.lower().strip()
    gateway_cls = _GATEWAYS.get(name)
    if gateway_cls is None:
        logger.error(
            f"Unknown SMS_PROVIDER '{settings.SMS_PROVIDER}' (available: {', '.join(_GATEWAYS)}). "
            "Falling back to the dry-run 'log' gateway."
        )
        gateway_cls = LogOnlySMSGateway
    return gateway_cls()
