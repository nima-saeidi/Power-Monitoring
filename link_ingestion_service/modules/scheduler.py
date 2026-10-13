import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

import aio_pika
import httpx

from core.config import settings
from modules.sources import LinkConfig, SourceError, get_source

logger = logging.getLogger("link_ingestion_scheduler")

METRIC_ROUTING_KEY = "link.metric"
OFFLINE_ROUTING_KEY = "link.alert.source_offline"
RECOVERED_ROUTING_KEY = "link.alert.source_recovered"


def _internal_headers() -> dict:
    return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}


def _to_link_config(raw: dict) -> Optional[LinkConfig]:
    link_id = raw.get("link_id")
    provider = raw.get("provider")
    external_id = raw.get("external_id")
    if not (link_id and provider and external_id):
        return None
    try:
        interval = max(int(raw.get("interval") or settings.LINK_POLL_INTERVAL), 1)
    except (TypeError, ValueError):
        interval = settings.LINK_POLL_INTERVAL
    return LinkConfig(
        link_id=int(link_id),
        provider=str(provider),
        external_id=str(external_id),
        interval=interval,
        name=raw.get("name"),
        feeder_id=raw.get("feeder_id"),
        allowed_current=raw.get("allowed_current"),
        field_map=raw.get("field_map") or {},
        options=raw.get("options") or {},
    )


class LinkIngestionScheduler:
    """Keeps one polling task per configured link, in sync with main_api.

    Readings are published to the telemetry exchange as `link.metric`; the
    timeseries_storage service writes them to InfluxDB (`link_telemetry`).
    """

    def __init__(self):
        self.is_running = False
        self._tasks: Dict[int, asyncio.Task] = {}
        self._fingerprints: Dict[int, str] = {}
        self._sync_task: Optional[asyncio.Task] = None
        # link_id -> last config problem logged, so each problem is logged once, not every sync.
        self._skipped: Dict[int, str] = {}
        self._http: Optional[httpx.AsyncClient] = None

        self._rmq_connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def _init_rabbitmq(self):
        self._rmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await self._rmq_connection.channel()
        self._exchange = await channel.declare_exchange(
            name=settings.TELEMETRY_EXCHANGE, type=aio_pika.ExchangeType.TOPIC, durable=True
        )
        logger.info(f"✅ RabbitMQ publisher connected. Exchange: '{settings.TELEMETRY_EXCHANGE}'")

    async def _publish(self, routing_key: str, payload: dict):
        if not self._exchange:
            logger.error("RabbitMQ exchange is not ready. Message dropped.")
            return
        try:
            message = aio_pika.Message(
                body=json.dumps(payload, default=str).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self._exchange.publish(message, routing_key=routing_key)
        except Exception as e:
            logger.error(f"❌ Error publishing event to {routing_key}: {e}")

    async def _fetch_link_configs(self) -> Optional[list[LinkConfig]]:
        """None means main_api was unreachable - keep the current tasks running."""
        url = f"{settings.MAIN_API_URL.rstrip('/')}/links/internal/active-sources"
        try:
            response = await self._http.get(url, headers=_internal_headers(), timeout=10.0)
        except Exception as e:
            logger.error(f"Cannot connect to main_api at {url}: {e!r}")
            return None
        if response.status_code != 200:
            logger.error(f"Failed to fetch link sources. Status: {response.status_code} | Body: {response.text}")
            return None
        configs = []
        for raw in response.json():
            config = _to_link_config(raw)
            if config is None:
                logger.warning(f"Skipping invalid link source config: {raw}")
                continue
            configs.append(config)
        return configs

    async def poll_link(self, link: LinkConfig):
        source = get_source(link.provider)
        failures = 0
        is_online = True

        try:
            while self.is_running:
                try:
                    reading = await source.fetch(self._http, link)
                except asyncio.CancelledError:
                    raise
                except SourceError as e:
                    reading, error = None, str(e)
                except Exception as e:
                    logger.error(f"Unexpected error reading link {link.link_id}", exc_info=True)
                    reading, error = None, f"Unexpected error: {e!r}"

                if reading is not None:
                    if failures and not is_online:
                        await self._publish(RECOVERED_ROUTING_KEY, {
                            "link_id": link.link_id,
                            "feeder_id": link.feeder_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info(f"✅ Link {link.link_id} source is back online.")
                    failures, is_online = 0, True
                    await self._publish(METRIC_ROUTING_KEY, {
                        "link_id": link.link_id,
                        "feeder_id": link.feeder_id,
                        "provider": link.provider,
                        "values": reading.values,
                        "timestamp": reading.timestamp.isoformat(),
                    })
                    logger.debug(f"📊 Link {link.link_id} | {reading.values}")
                else:
                    failures += 1
                    logger.warning(f"⚠️ Link {link.link_id} ({link.provider}:{link.external_id}) "
                                   f"read failed [{failures}]: {error}")
                    if failures >= settings.LINK_MAX_FAILURES and is_online:
                        is_online = False
                        await self._publish(OFFLINE_ROUTING_KEY, {
                            "link_id": link.link_id,
                            "feeder_id": link.feeder_id,
                            "failures_count": failures,
                            "error_message": error,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                await asyncio.sleep(link.interval if is_online else settings.LINK_OFFLINE_RETRY_INTERVAL)
        except asyncio.CancelledError:
            logger.info(f"🛑 Polling task cancelled for Link ID {link.link_id}")

    def _stop_task(self, link_id: int):
        task = self._tasks.pop(link_id, None)
        self._fingerprints.pop(link_id, None)
        if task and not task.done():
            task.cancel()

    async def _sync_links_loop(self):
        while self.is_running:
            try:
                configs = await self._fetch_link_configs()
                if configs is not None:
                    wanted_ids = set()
                    for link in configs:
                        source = get_source(link.provider)
                        problem = None
                        if source is None:
                            problem = f"unknown provider '{link.provider}'"
                        elif not source.is_configured(link):
                            problem = f"provider '{link.provider}' is not configured"
                        if problem:
                            if self._skipped.get(link.link_id) != problem:
                                logger.warning(f"Link {link.link_id} skipped: {problem}.")
                                self._skipped[link.link_id] = problem
                            continue
                        self._skipped.pop(link.link_id, None)

                        wanted_ids.add(link.link_id)
                        fingerprint = link.fingerprint()
                        if link.link_id in self._tasks and self._fingerprints.get(link.link_id) != fingerprint:
                            logger.info(f"🔄 Config changed for Link ID {link.link_id}. Restarting task...")
                            self._stop_task(link.link_id)

                        task = self._tasks.get(link.link_id)
                        if task is None or task.done():
                            self._tasks[link.link_id] = asyncio.create_task(self.poll_link(link))
                            self._fingerprints[link.link_id] = fingerprint
                            logger.info(f"➕ Started ingestion for Link ID {link.link_id} "
                                        f"({link.provider}:{link.external_id}) every {link.interval}s.")

                    for stale_id in set(self._tasks) - wanted_ids:
                        logger.info(f"➖ Link ID {stale_id} no longer has an active source. Stopping task...")
                        self._stop_task(stale_id)
            except Exception as e:
                logger.error(f"❌ Error during link synchronization: {e}", exc_info=True)

            await asyncio.sleep(settings.LINK_SOURCE_SYNC_INTERVAL)

    async def start(self):
        self.is_running = True
        logger.info("🚀 Starting Link Ingestion Scheduler...")
        self._http = httpx.AsyncClient(verify=settings.LINK_API_VERIFY_SSL)
        await self._init_rabbitmq()
        self._sync_task = asyncio.create_task(self._sync_links_loop())

    async def stop(self):
        logger.info("🛑 Stopping Link Ingestion Scheduler...")
        self.is_running = False

        tasks = list(self._tasks.values())
        if self._sync_task:
            tasks.append(self._sync_task)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._fingerprints.clear()

        if self._http:
            await self._http.aclose()
        if self._rmq_connection and not self._rmq_connection.is_closed:
            await self._rmq_connection.close()
        logger.info("All link ingestion tasks cleanly stopped.")
