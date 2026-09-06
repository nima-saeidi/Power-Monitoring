import asyncio
import json
import logging
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

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode())
            await handle_telemetry_metric(payload)
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)

async def main():
    logger.info("Connecting to InfluxDB...")
    await db_client.connect()

    logger.info("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=50)

    exchange = await channel.declare_exchange(
        settings.TELEMETRY_EXCHANGE,
        aio_pika.ExchangeType.TOPIC,
        durable=True
    )

    queue = await channel.declare_queue(
        settings.TIMESERIES_QUEUE,
        durable=True
    )
    await queue.bind(exchange, routing_key=settings.ROUTING_KEY)

    await queue.consume(process_message)
    logger.info(f"🚀 TimeSeries Storage Service is listening on queue: {settings.TIMESERIES_QUEUE}")

    try:
        await asyncio.Future()  # اجرای نامحدود ورکر
    finally:
        await connection.close()
        await db_client.close()

if __name__ == "__main__":
    asyncio.run(main())
