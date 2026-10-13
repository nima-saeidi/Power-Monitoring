import logging
from core.influx_client import db_client

logger = logging.getLogger(__name__)


async def handle_telemetry_metric(payload: dict):
    data = payload.get("data", payload)

    feeder_id = data.get("feeder_id") or payload.get("feeder_id")
    timestamp = payload.get("timestamp") or data.get("timestamp")

    if not feeder_id:
        logger.warning(f"Payload missing feeder_id: {payload}")
        return

    await db_client.write_telemetry(
        feeder_id=feeder_id,
        data=data,
        timestamp=timestamp
    )
    logger.info(f"📈 Stored time-series for feeder_id: {feeder_id}")


async def handle_link_metric(payload: dict):
    link_id = payload.get("link_id")
    values = payload.get("values")
    if not link_id or not isinstance(values, dict):
        logger.warning(f"Invalid link metric payload: {payload}")
        return

    written = await db_client.write_link_telemetry(
        link_id=link_id,
        values=values,
        timestamp=payload.get("timestamp"),
        feeder_id=payload.get("feeder_id"),
        provider=payload.get("provider"),
    )
    if written:
        logger.info(f"📈 Stored time-series for link_id: {link_id}")
    else:
        logger.warning(f"Link metric for link_id {link_id} had no numeric values: {values}")
