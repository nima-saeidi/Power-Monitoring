import json
import logging
import asyncio
import aio_pika
from core.config import settings
from modules.services import logging_service_instance
from modules.schemas import LogCreate

try:
    from pygelf import GelfUdpHandler
except ImportError:
    GelfUdpHandler = None
    logging.warning("pygelf is not installed. Logs will not be sent to Graylog.")

logger = logging.getLogger(__name__)

graylog_logger = logging.getLogger("graylog_audit")
graylog_logger.setLevel(logging.INFO)

if GelfUdpHandler and not graylog_logger.handlers:
    graylog_logger.addHandler(
        GelfUdpHandler(host=settings.GRAYLOG_HOST, port=settings.GRAYLOG_PORT)
    )



async def process_audit_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        try:
            body = message.body.decode("utf-8")
            data = json.loads(body)

            valid_log = LogCreate(**data)
            logger.info(f"Received audit log: {valid_log.action} from {valid_log.service_name}")

            await logging_service_instance.save_log(valid_log)

            if GelfUdpHandler:
                details = valid_log.details or {}
                level_str = str(details.get("severity", "INFO")).upper()
                level_map = {
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL
                }
                log_level = level_map.get(level_str, logging.INFO)

                extra_fields = {
                    "_service_name": valid_log.service_name,
                    "_audit_action": valid_log.action,
                    "_user_id": valid_log.user_id,
                    "_success": details.get("success"),
                    "_username": details.get("username"),
                    "_extra_data": str(details)
                }

                msg_text = details.get("description") or f"Audit Log: {valid_log.action}"
                graylog_logger.log(log_level, msg_text, extra=extra_fields)

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to decode message JSON: {jde}")
            raise
        except Exception as e:
            logger.error(f"Error processing audit message: {e}", exc_info=True)
            raise


async def _declare_logs_queue_with_dlq(connection, channel):
    queue_name = "logs_queue"
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


async def start_consumer():
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        queue, channel = await _declare_logs_queue_with_dlq(connection, channel)
        await queue.consume(process_audit_message)

        logger.info("RabbitMQ Consumer started successfully. Listening to 'logs_queue'...")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect or start RabbitMQ consumer: {e}")
        await asyncio.sleep(5)
        return await start_consumer()
