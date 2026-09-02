import json
import logging
import asyncio
import aio_pika
from core.config import settings
from modules.services import logging_service_instance

# تلاش برای ایمپورت GelfUdpHandler جهت ارسال به Graylog
try:
    from pygelf import GelfUdpHandler
except ImportError:
    GelfUdpHandler = None
    logging.warning("pygelf is not installed. Logs will not be sent to Graylog.")

logger = logging.getLogger(__name__)

RABBITMQ_URL = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

# ---------------- تنظیمات لاگر Graylog ----------------
GRAYLOG_HOST = getattr(settings, "GRAYLOG_HOST", "graylog")
GRAYLOG_PORT = int(getattr(settings, "GRAYLOG_PORT", 12201))

graylog_logger = logging.getLogger("graylog_audit")
graylog_logger.setLevel(logging.INFO)

# افزودن هندلر GELF به لاگر مخصوص Graylog (جلوگیری از افزودن چندباره)
if GelfUdpHandler and not graylog_logger.handlers:
    graylog_logger.addHandler(GelfUdpHandler(host=GRAYLOG_HOST, port=GRAYLOG_PORT))


# ------------------------------------------------------


async def process_audit_message(message: aio_pika.IncomingMessage):
    """پردازش و ذخیره پیام دریافتی از صف در دیتابیس PostgreSQL و ارسال همزمان به Graylog"""
    async with message.process(requeue=False):
        try:
            body = message.body.decode("utf-8")
            data = json.loads(body)
            action = data.get('action', 'UNKNOWN')
            logger.info(f"Received audit log: {action}")

            # ۱. ذخیره در PostgreSQL از طریق سرویس
            await logging_service_instance.save_log(data)

            # ۲. ارسال به Graylog
            if GelfUdpHandler:
                # مپ کردن سطح لاگ (رشته) به سطح استاندارد logging پایتون
                level_str = str(data.get("level", "INFO")).upper()
                level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL
                }
                log_level = level_map.get(level_str, logging.INFO)

                # فیلدهای اضافی برای اینکه در پنل Graylog به صورت مجزا قابل سرچ و فیلتر باشند
                extra_fields = {
                    "service_name": data.get("service", "unknown"),
                    "audit_action": action,
                    "user_id": data.get("user_id"),
                    "extra_data": str(data.get("extra_data", {}))
                }

                # ارسال رکورد به Graylog
                graylog_logger.log(
                    log_level,
                    data.get("message", f"Audit Log Received: {action}"),
                    extra=extra_fields
                )

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
