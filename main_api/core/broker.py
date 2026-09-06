import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from main_api.core.config import settings

logger = logging.getLogger(__name__)


class MessageBroker:
    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.exchange: Optional[aio_pika.RobustExchange] = None

    @property
    def is_connected(self) -> bool:
        """بررسی وضعیت فعال بودن اتصال"""
        return bool(self.connection and not self.connection.is_closed and self.channel and not self.channel.is_closed)

    async def connect(self):
        """برقراری اتصال پایدار و تنظیم اکسچنج اصلی"""
        rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            # افزایش prefetch_count برای کارایی بالاتر
            await self.channel.set_qos(prefetch_count=10)

            # تعریف اکسچنج از نوع Topic برای معماری Event-Driven / CQRS
            self.exchange = await self.channel.declare_exchange(
                name="power_monitoring_events",
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("✅ Successfully connected to RabbitMQ and declared topic exchange.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            self.exchange = None

    async def close(self):
        """قطع ایمن اتصال"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish(self, routing_key: str, message: Dict[str, Any], queue_name: Optional[str] = None):
        """
        ارسال رویداد/پیام به RabbitMQ
        - اگر اکسچنج فعال باشد، بر اساس routing_key به اکسچنج ارسال می‌کند.
        - در غیر این صورت، مستقیماً به صف پیش‌فرض ارسال می‌نماید.
        """
        if not self.channel or self.channel.is_closed:
            logger.warning(f"Cannot publish event to '{routing_key}', RabbitMQ channel is not active.")
            return

        try:
            body = json.dumps(message, default=str).encode("utf-8")
            pika_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )

            if self.exchange:
                await self.exchange.publish(pika_message, routing_key=routing_key)
            else:
                target_queue = queue_name or routing_key
                await self.channel.declare_queue(target_queue, durable=True)
                await self.channel.default_exchange.publish(pika_message, routing_key=target_queue)

            logger.debug(f"Published message with routing_key: '{routing_key}'")
        except Exception as e:
            logger.error(f"Error publishing message to {routing_key}: {e}")


# نمونه سراسری بروکر
message_broker = MessageBroker()
# نام مستعار جهت سازگاری با کلاس‌های قدیمی
RabbitMQPublisher = MessageBroker


def get_rabbitmq_publisher() -> MessageBroker:
    """تابع وابستگی (Dependency Injection) برای استفاده در FastAPI Depends"""
    return message_broker


async def send_log_to_rabbitmq(
    level: str,
    message: str,
    service: str = "main_api",
    extra_data: Optional[Dict[str, Any]] = None,
    routing_key: str = "audit_logs",
    **kwargs
):
    """ارسال لاگ‌های سیستمی به RabbitMQ"""
    payload_extra = extra_data or {}
    if kwargs:
        payload_extra.update(kwargs)

    log_payload = {
        "service_name": service,
        "level": level.upper(),
        "message": message,
        "extra_data": payload_extra
    }
    await message_broker.publish(routing_key=routing_key, message=log_payload, queue_name=routing_key)
