import asyncio
import json
import logging
import os
import sys
from pathlib import Path
import aio_pika

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from core.config import settings
from core.influx_client import db_client
from core.telemetry import handle_telemetry_metric

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("timeseries_storage_service")

# Ship every logger's records to Graylog (root logger, not just this one) -
# ops has no server access, only the Graylog port. Never fatal on failure.
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

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode())
            await handle_telemetry_metric(payload)
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            raise


async def _declare_main_queue_with_dlq(connection, channel, queue_name: str):
    dlx_name = f"{queue_name}.dlx"
    dlq_name = f"{queue_name}.dlq"
    try:
        dlx_exchange = await channel.declare_exchange(dlx_name, aio_pika.ExchangeType.FANOUT, durable=True)
        dlq = await channel.declare_queue(dlq_name, durable=True)
        await dlq.bind(dlx_exchange)
        queue = await channel.declare_queue(
            queue_name, durable=True, arguments={"x-dead-letter-exchange": dlx_name}
        )
        return queue, channel
    except aio_pika.exceptions.ChannelClosed:
        logger.error(
            f"Queue '{queue_name}' already exists with incompatible arguments. "
            "Falling back WITHOUT dead-letter support; delete the queue manually once to enable DLQ."
        )
        fresh_channel = await connection.channel()
        await fresh_channel.set_qos(prefetch_count=50)
        queue = await fresh_channel.declare_queue(queue_name, durable=True)
        return queue, fresh_channel


async def main():
    logger.info("Connecting to InfluxDB...")
    await db_client.connect()

    logger.info("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=50)

    queue, channel = await _declare_main_queue_with_dlq(connection, channel, settings.TIMESERIES_QUEUE)

    exchange = await channel.declare_exchange(
        settings.TELEMETRY_EXCHANGE,
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    await queue.bind(exchange, routing_key=settings.ROUTING_KEY)

    await queue.consume(process_message)
    logger.info(f"🚀 TimeSeries Storage Service is listening on queue: {settings.TIMESERIES_QUEUE}")

    try:
        await asyncio.Future()
    finally:
        await connection.close()
        await db_client.close()

if __name__ == "__main__":
    asyncio.run(main())
