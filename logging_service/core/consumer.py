import json
import logging
import asyncio
import aio_pika
from core.config import settings
from modules.services import logging_service_instance

logger = logging.getLogger(__name__)

RABBITMQ_URL = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


async def process_audit_message(message: aio_pika.IncomingMessage):
    """پردازش و ذخیره پیام دریافتی از صف در دیتابیس PostgreSQL"""
    async with message.process(requeue=False):
        try:
            body = message.body.decode("utf-8")
            data = json.loads(body)
            logger.info(f"Received audit log: {data.get('action', 'UNKNOWN')}")

            # ذخیره در PostgreSQL از طریق سرویس
            await logging_service_instance.save_log(data)

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to decode message JSON: {jde}")
        except Exception as e:
            logger.error(f"Error processing audit message: {e}", exc_info=True)


async def start_consumer():
    """اتصال به RabbitMQ و گوش دادن به صف audit_logs"""
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # تعریف صف durable برای جلوگیری از پاک شدن پیام‌ها حین ریستارت
        queue = await channel.declare_queue("audit_logs", durable=True)
        await queue.consume(process_audit_message)

        logger.info("RabbitMQ Consumer started successfully. Listening to 'audit_logs'...")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect or start RabbitMQ consumer: {e}")
        raise e
