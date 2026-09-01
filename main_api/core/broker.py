import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from main_api.core.config import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MessageBroker:
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None

    async def connect(self):
        """برقراری اتصال پایدار به RabbitMQ"""
        rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            logger.info("✅ Successfully connected to RabbitMQ.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None

    async def close(self):
        """قطع ایمن اتصال"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish(self, queue_name: str, message: Dict[str, Any]):
        """ارسال پیام به صف مشخص"""
        if not self.channel:
            logger.warning(f"Cannot publish to '{queue_name}', RabbitMQ channel is not active.")
            return

        try:
            # اطمینان از وجود صف (Durable)
            queue = await self.channel.declare_queue(queue_name, durable=True)
            body = json.dumps(message, default=str).encode("utf-8")

            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue.name
            )
            logger.debug(f"Published message to {queue_name}")
        except Exception as e:
            logger.error(f"Error publishing message to {queue_name}: {e}")


# نمونه سراسری بروکر
message_broker = MessageBroker()


async def send_log_to_rabbitmq(
    level: str,
    message: str,
    service: str = "main_api",
    extra_data: dict[str, Any] | None = None,
    queue_name: str = "audit_logs",
    **kwargs
):
    """ارسال لاگ به صف RabbitMQ"""
    payload_extra = extra_data or {}
    if kwargs:
        payload_extra.update(kwargs)

    log_payload = {
        "service_name": service,
        "level": level.upper(),
        "message": message,
        "extra_data": payload_extra
    }
    await message_broker.publish(queue_name=queue_name, message=log_payload)
