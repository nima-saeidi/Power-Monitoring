# logging_service/core/consumer.py
import json
import logging
import asyncio
import aio_pika
from core.config import settings
from modules.services import logging_service_instance
from modules.schemas import LogCreate  # اضافه شدن برای اعتبارسنجی

try:
    from pygelf import GelfUdpHandler
except ImportError:
    GelfUdpHandler = None
    logging.warning("pygelf is not installed. Logs will not be sent to Graylog.")

logger = logging.getLogger(__name__)

# ---------------- تنظیمات لاگر Graylog ----------------
graylog_logger = logging.getLogger("graylog_audit")
graylog_logger.setLevel(logging.INFO)

if GelfUdpHandler and not graylog_logger.handlers:
    graylog_logger.addHandler(
        GelfUdpHandler(host=settings.GRAYLOG_HOST, port=settings.GRAYLOG_PORT)
    )


# ------------------------------------------------------

async def process_audit_message(message: aio_pika.IncomingMessage):
    """پردازش و ذخیره پیام دریافتی از صف در دیتابیس PostgreSQL و ارسال همزمان به Graylog"""
    async with message.process(requeue=False):
        try:
            body = message.body.decode("utf-8")
            data = json.loads(body)

            # اعتبارسنجی ساختار داده با Pydantic (جلوگیری از دیتای ناقص)
            valid_log = LogCreate(**data)
            logger.info(f"Received audit log: {valid_log.action} from {valid_log.service_name}")

            # ۱. ذخیره در PostgreSQL
            await logging_service_instance.save_log(valid_log)

            # ۲. ارسال به Graylog
            if GelfUdpHandler:
                level_str = str(data.get("level", "INFO")).upper()
                level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL
                }
                log_level = level_map.get(level_str, logging.INFO)

                # فیلدهای اضافی برای پنل Graylog
                extra_fields = {
                    "_service_name": valid_log.service_name,
                    "_audit_action": valid_log.action,
                    "_user_id": valid_log.user_id,
                    "_extra_data": str(valid_log.details)
                }

                # ارسال پیام به گری‌لاگ
                msg_text = data.get("message", f"Audit Log: {valid_log.action}")
                graylog_logger.log(log_level, msg_text, extra=extra_fields)

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to decode message JSON: {jde}")
        except Exception as e:
            logger.error(f"Error processing audit message: {e}", exc_info=True)


async def start_consumer():
    """اتصال به RabbitMQ و گوش دادن به صف audit_logs"""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        queue = await channel.declare_queue("logs_queue", durable=True)
        await queue.consume(process_audit_message)

        logger.info("RabbitMQ Consumer started successfully. Listening to 'logs_queue'...")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect or start RabbitMQ consumer: {e}")
        # اتصال مجدد در صورت قطعی ربیت‌ام‌کیو در زمان بوت
        await asyncio.sleep(5)
        return await start_consumer()
