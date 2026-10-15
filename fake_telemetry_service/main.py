"""Demo telemetry generator.

Fills InfluxDB history for feeders that have a gap, then publishes a synthetic
`telemetry.metric` for each selected feeder every FAKE_INTERVAL seconds - the
same event the real Modbus poller publishes - so the dashboard, WebSocket,
charts, reports and energy endpoints all have data on a server without
reachable devices.

Started only with the compose profile `demo`:
    docker compose --profile demo up -d --build fake_telemetry
"""
import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timedelta, timezone
from typing import Dict

import aio_pika
import httpx
from influxdb_client import Point, WritePrecision
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from config import settings
from load_profile import sample

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fake_telemetry_service")
logging.getLogger("httpx").setLevel(logging.WARNING)

try:
    import graypy
    _gelf_handler = graypy.GELFUDPHandler(
        os.getenv("GRAYLOG_HOST", "graylog"),
        int(os.getenv("GRAYLOG_PORT", "12201")),
        debugging_fields=True,
        extra_fields=True,
    )
    _gelf_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(_gelf_handler)
except Exception as _graylog_err:
    logger.warning(f"Could not attach Graylog handler: {_graylog_err}")


async def fetch_feeders() -> Dict[int, dict]:
    url = f"{settings.MAIN_API_URL.rstrip('/')}/telemetry/active-feeders"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY})
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Cannot read active feeders from {url}: {e}")
        return {}

    only = settings.feeder_filter
    feeders = {}
    for cfg in response.json():
        if only is not None and cfg["feeder_id"] not in only:
            continue
        if settings.FAKE_ONLY_OFFLINE and cfg.get("is_online", True):
            continue
        feeders[cfg["feeder_id"]] = cfg
    return feeders


async def _last_point(query_api, feeder_id: int):
    flux = f'''
        from(bucket: "{settings.INFLUXDB_BUCKET}")
          |> range(start: -{settings.FAKE_BACKFILL_DAYS}d)
          |> filter(fn: (r) => r._measurement == "feeder_telemetry" and r.feeder_id == "{feeder_id}"
                               and r._field == "current")
          |> last()
    '''
    tables = await query_api.query(flux, org=settings.INFLUXDB_ORG)
    times = [record.get_time() for table in tables for record in table.records]
    return max(times) if times else None


async def backfill(feeders: Dict[int, dict]) -> None:
    if settings.FAKE_BACKFILL_DAYS <= 0 or not feeders:
        return
    step = timedelta(seconds=settings.FAKE_BACKFILL_STEP_SECONDS)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    async with InfluxDBClientAsync(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN,
                                   org=settings.INFLUXDB_ORG, timeout=60_000) as client:
        query_api, write_api = client.query_api(), client.write_api()
        for fid, cfg in feeders.items():
            last = await _last_point(query_api, fid)
            start = (last + step) if last else now - timedelta(days=settings.FAKE_BACKFILL_DAYS)
            if now - start < step * 2:
                continue
            points, written, ts = [], 0, start
            while ts < now:
                point = Point("feeder_telemetry").tag("feeder_id", str(fid))
                for field, value in sample(ts, fid, cfg.get("max_current"), cfg.get("feeder_type")).items():
                    point = point.field(field, float(value))
                points.append(point.time(ts, WritePrecision.S))
                ts += step
                if len(points) >= 5000:
                    await write_api.write(bucket=settings.INFLUXDB_BUCKET, record=points)
                    written += len(points)
                    points = []
            if points:
                await write_api.write(bucket=settings.INFLUXDB_BUCKET, record=points)
                written += len(points)
            logger.info(f"Backfilled feeder {fid}: {written} points from {start:%Y-%m-%d %H:%M} UTC")


async def run(stop: asyncio.Event) -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(settings.TELEMETRY_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    feeders: Dict[int, dict] = {}
    next_sync = 0.0
    loop = asyncio.get_running_loop()
    try:
        while not stop.is_set():
            if loop.time() >= next_sync:
                fresh = await fetch_feeders()
                if fresh.keys() != feeders.keys():
                    logger.info(f"Generating demo telemetry for feeders: {sorted(fresh) or 'none'}")
                    await backfill({fid: cfg for fid, cfg in fresh.items() if fid not in feeders})
                feeders = fresh
                next_sync = loop.time() + settings.FAKE_SYNC_INTERVAL

            now = datetime.now(timezone.utc)
            for fid, cfg in feeders.items():
                body = {"feeder_id": fid, **sample(now, fid, cfg.get("max_current"), cfg.get("feeder_type")),
                        "timestamp": now.isoformat()}
                await exchange.publish(
                    aio_pika.Message(json.dumps(body).encode("utf-8"), content_type="application/json",
                                     delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                    routing_key="telemetry.metric",
                )
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.FAKE_INTERVAL)
            except asyncio.TimeoutError:
                pass
    finally:
        await connection.close()


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows dev machines
            pass

    while not stop.is_set():
        try:
            await run(stop)
        except Exception as e:
            logger.error(f"Demo telemetry loop crashed, restarting in 10s: {e}", exc_info=True)
            try:
                await asyncio.wait_for(stop.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
