import json
import logging
from core.influx_client import db_client

logger = logging.getLogger(__name__)


async def handle_telemetry_metric(payload: dict):
    """دریافت پیام و ارسال به InfluxDB"""
    feeder_id = payload.get("feeder_id")
    timestamp = payload.get("timestamp")

    if not feeder_id:
        logger.warning(f"Payload missing feeder_id: {payload}")
        return

    await db_client.write_telemetry(
        feeder_id=feeder_id,
        data=payload,
        timestamp=timestamp
    )
    logger.info(f"📈 Stored time-series for feeder_id: {feeder_id}")
