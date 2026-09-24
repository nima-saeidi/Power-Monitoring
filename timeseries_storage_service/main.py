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
    # با requeue=False، پیام ناموفق nack می‌شود و چون صف با x-dead-letter-exchange
    # declare شده، به‌جای گم شدن کامل به صف <queue>.dlq منتقل می‌شود.
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode())
            await handle_telemetry_metric(payload)
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            raise  # تا message.process() آن را nack کند (به DLQ) نه ack بی‌صدا


async def _declare_main_queue_with_dlq(connection, channel, queue_name: str):
    """مشابه توضیح در postgres_storage_service/main.py: declare صف با DLQ، با fallback امن اگر صف قبلاً بدون این آرگومان وجود داشته باشد."""
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
        logger.warning(
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

    # نکته: صف اول declare می‌شود (که ممکن است در صورت fallback کانال را عوض کند)
    # و بعد Exchange با همان کانال نهایی declare می‌شود، تا exchange/queue حتماً
    # روی یک کانال یکسان باشند و bind با خطا مواجه نشود.
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
        await asyncio.Future()  # اجرای نامحدود ورکر
    finally:
        await connection.close()
        await db_client.close()

if __name__ == "__main__":
    asyncio.run(main())
