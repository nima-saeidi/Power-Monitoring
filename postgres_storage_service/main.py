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
    # با requeue=False اگر پردازش با خطا مواجه شود، پیام در صف قفل نمی‌شود (یا به DLQ می‌رود)
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
            logger.error("Failed to decode message JSON. Dropping invalid message.")
        except Exception as e:
            logger.exception(f"Unhandled error processing message: {e}")
            # در صورتی که می‌خواهید پیام‌های خطادار دوباره وارد صف شوند (برای خطاهای موقت شبکه):
            # await message.reject(requeue=True)


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

                # تعریف صف با قابلیت دوام (Durable)
                queue = await channel.declare_queue("db.settings.write", durable=True)

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
