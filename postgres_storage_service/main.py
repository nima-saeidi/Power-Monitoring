import asyncio
import json
import logging
import sys
from pathlib import Path
import aio_pika

# تضمین شناسایی ماژول‌ها فارغ از مسیر اجرای ترمینال
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from core.config import settings
except ModuleNotFoundError:
    # در صورتی که config مستقیما در پوشه جاری باشد
    from config import settings

from handlers import handle_db_write_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("postgres_storage_worker")


async def process_message(message: aio_pika.IncomingMessage) -> None:
    """پردازش هر پیام دریافتی از صف RabbitMQ"""
    # با requeue=False، پیامی که پردازشش استثنا بدهد nack می‌شود؛ چون صف با
    # آرگومان x-dead-letter-exchange declare شده، این پیام گم نمی‌شود بلکه به
    # صف db.settings.write.dlq منتقل می‌شود تا بعداً بررسی/reprocess شود.
    async with message.process(requeue=False, ignore_processed=True):
        try:
            payload = json.loads(message.body.decode("utf-8"))
            routing_key = message.routing_key or "unknown"
            logger.info(f"Processing event from [{routing_key}]")
            logger.debug(f"Payload: {payload}")

            # ارسال به هندلر مربوط به دیتابیس
            await handle_db_write_event(payload)
            logger.info(f"Successfully processed event: {payload.get('event_type', 'N/A')}")

        except json.JSONDecodeError:
            logger.error("Failed to decode message JSON. Sending to DLQ.")
            raise
        except Exception as e:
            logger.exception(f"Unhandled error processing message: {e}")
            # raise می‌شود تا message.process() آن را nack کند و به DLQ برود
            # (به‌جای بلعیدن خطا که باعث می‌شد پیام برای همیشه گم شود)
            raise


async def _declare_main_queue_with_dlq(connection, channel, queue_name: str):
    """
    Declare صف اصلی با آرگومان x-dead-letter-exchange. اگر این صف از قبل (قبل
    از این تغییر) با آرگومان‌های متفاوت روی RabbitMQ وجود داشته باشد، AMQP
    خطای PRECONDITION_FAILED می‌دهد که کانال جاری را می‌بندد؛ در این حالت با
    یک کانال تازه، صف را بدون DLQ declare می‌کنیم تا سرویس بالا بیاید (فقط
    بدون محافظت DLQ، تا زمانی که صف قدیمی یک‌بار به‌صورت دستی حذف شود).
    """
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
        await fresh_channel.set_qos(prefetch_count=10)
        queue = await fresh_channel.declare_queue(queue_name, durable=True)
        return queue, fresh_channel


async def run_worker() -> None:
    """حلقه اصلی اجرای کانسومر و اتصال پایدار به RabbitMQ"""
    logger.info("Starting Postgres Storage Worker...")

    while True:
        try:
            # ایجاد اتصال پایدار به RabbitMQ
            connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                client_properties={"connection_name": "postgres_storage_consumer"}
            )

            async with connection:
                channel = await connection.channel()
                # محدود کردن تعداد پیام‌های همزمان برای جلوگیری از سرریز حافظه
                await channel.set_qos(prefetch_count=10)

                # تعریف صف با قابلیت دوام (Durable) + Dead-Letter-Exchange تا
                # پیام‌هایی که پردازششان با خطا مواجه می‌شود (به‌جای گم شدن
                # کامل) به صف db.settings.write.dlq منتقل و قابل بررسی شوند.
                queue, channel = await _declare_main_queue_with_dlq(connection, channel, "db.settings.write")

                # تعریف Exchange از نوع Topic
                exchange = await channel.declare_exchange(
                    "power_monitoring_events",
                    type=aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )

                # بایند کردن الگوهای روتینگ به صف
                await queue.bind(exchange, routing_key="db.settings.*")
                await queue.bind(exchange, routing_key="db.users.*")
                await queue.bind(exchange, routing_key="db.telemetry.*")

                logger.info("Worker is ready and listening on queue 'db.settings.write'...")

                # شروع مصرف پیام‌ها
                await queue.consume(process_message)

                # زنده نگه داشتن کانسومر تا زمان دریافت سیگنال توقف
                stop_event = asyncio.Event()
                await stop_event.wait()

        except asyncio.CancelledError:
            logger.info("Worker task cancelled. Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"RabbitMQ connection lost/failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Postgres Storage Worker stopped by user.")
