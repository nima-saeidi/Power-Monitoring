import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from main_api.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """کلاس مدیریت اتصال و ارسال پیام‌ها به RabbitMQ"""
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None

    @property
    def is_connected(self) -> bool:
        """بررسی فعال بودن اتصال برای Health Check"""
        return bool(
            self.connection
            and not self.connection.is_closed
            and self.channel
            and not self.channel.is_closed
        )

    async def connect(self):
        """برقراری اتصال پایدار به RabbitMQ و راه‌اندازی Topic Exchange"""
        rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            # تعریف Topic Exchange برای مسیریابی بر اساس routing_key
            self.exchange = await self.channel.declare_exchange(
                name="power_monitoring_events",
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("✅ Connected to RabbitMQ and declared Topic Exchange.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            self.exchange = None

    async def close(self):
        """قطع اتصال در زمان Shutdown"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish_event(self, routing_key: str, message: Dict[str, Any]):
        """ارسال رویداد با استفاده از routing_key به Topic Exchange"""
        if not self.channel or not self.exchange:
            logger.warning(f"RabbitMQ is not connected. Cannot publish to '{routing_key}'.")
            return

        try:
            body = json.dumps(message, default=str).encode("utf-8")
            msg = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await self.exchange.publish(msg, routing_key=routing_key)
            logger.debug(f"Event published to routing_key: {routing_key}")
        except Exception as e:
            logger.error(f"Error publishing event to {routing_key}: {e}")

    async def publish(self, queue_name: str, message: Dict[str, Any], routing_key: Optional[str] = None):
        """متد کمکی برای ارسال به صف مستقیم یا استفاده عمومی"""
        if routing_key and self.exchange:
            await self.publish_event(routing_key, message)
        elif self.channel:
            body = json.dumps(message, default=str).encode("utf-8")
            msg = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            queue = await self.channel.declare_queue(queue_name, durable=True)
            await self.channel.default_exchange.publish(msg, routing_key=queue.name)


# یکپارچه‌سازی نام‌ها برای جلوگیری از بروز ارور در کل پروژه
MessageBroker = RabbitMQPublisher

# شیء سراسری بروکر
message_broker = RabbitMQPublisher()


def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """تزریق وابستگی برای روت‌ها و سرویس‌های FastAPI"""
    return message_broker


async def send_log_to_rabbitmq(
    level: str,
    message: str,
    service: str = "main_api",
    extra_data: Optional[Dict[str, Any]] = None,
    queue_name: str = "audit_logs",
    **kwargs
):
    """ارسال لاگ‌ها به صف سیستم لاگینگ"""
    payload_extra = extra_data or {}
    if kwargs:
        payload_extra.update(kwargs)

    log_payload = {
        "service_name": service,
        "level": level.upper(),
        "message": message,
        "extra_data": payload_extra
    }
    await message_broker.publish_event(routing_key="logs.audit", message=log_payload)
