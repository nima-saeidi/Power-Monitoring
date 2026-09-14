import json
import logging
from typing import Any, Dict, Optional
import aio_pika
from datetime import datetime, timezone
from main_api.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """کلاس مدیریت اتصال و انتشار رویدادها به RabbitMQ از طریق Topic Exchange"""
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
            # تنظیم prefetch_count برای بهبود کارایی worker-ها
            await self.channel.set_qos(prefetch_count=10)

            # تعریف Topic Exchange اصلی برای مسیریابی رویدادها
            self.exchange = await self.channel.declare_exchange(
                name="power_monitoring_events",
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("✅ Successfully connected to RabbitMQ and declared Topic Exchange 'power_monitoring_events'.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            self.exchange = None

    async def close(self):
        """قطع ایمن اتصال در زمان خاموش شدن برنامه"""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish_event(self, routing_key: str, message: Dict[str, Any]):
        """
        متد اصلی برای انتشار رویدادها به Topic Exchange.
        تمام سرویس‌ها باید از این متد استفاده کنند.
        """
        if not self.exchange or not self.is_connected:
            logger.warning(f"RabbitMQ is not connected. Cannot publish event to routing_key '{routing_key}'.")
            # در یک سناریوی واقعی، می‌توان پیام را در یک صف موقت ذخیره و بعداً ارسال کرد
            return

        try:
            body = json.dumps(message, default=str).encode("utf-8")
            pika_message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT, # ذخیره پیام روی دیسک تا زمان تحویل
                content_type="application/json"
            )
            await self.exchange.publish(pika_message, routing_key=routing_key)
            logger.debug(f"Event published to exchange 'power_monitoring_events' with routing_key: '{routing_key}'")
        except Exception as e:
            logger.error(f"Error publishing event with routing_key '{routing_key}': {e}")


# نمونه سراسری بروکر
message_broker = RabbitMQPublisher()

# نام مستعار جهت سازگاری
MessageBroker = RabbitMQPublisher


def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """تابع وابستگی (Dependency Injection) برای استفاده در FastAPI"""
    return message_broker


async def send_log_to_rabbitmq(
    level: str,
    message: str,
    service: str = "main_api",
    extra_data: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """ارسال لاگ‌های سیستمی به RabbitMQ از طریق رویداد"""
    payload_extra = extra_data or {}
    if kwargs:
        payload_extra.update(kwargs)

    log_payload = {
        "service_name": service,
        "level": level.upper(),
        "message": message,
        "extra_data": payload_extra,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    # ارسال لاگ‌ها با routing_key مشخص برای پردازش در سرویس لاگ
    await message_broker.publish_event(routing_key="logs.audit", message=log_payload)
