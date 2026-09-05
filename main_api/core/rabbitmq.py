import json
import aio_pika
from typing import Any, Dict
import logging
from ..config import settings  # فرض بر این است آدرس RabbitMQ در تنظیمات موجود است

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self):
        self.connection: aio_pika.RobustConnection = None
        self.channel: aio_pika.RobustChannel = None
        self.exchange: aio_pika.RobustExchange = None
        self.exchange_name = "power_monitoring_exchange"

    async def connect(self):
        """ایجاد اتصال پایدار به RabbitMQ و تعریف Exchange"""
        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL  # مثلاً: "amqp://guest:guest@rabbitmq:5672/"
            )
            self.channel = await self.connection.channel()

            # تعریف Exchange از نوع Fanout برای ارسال داده به هر دو سرویس
            self.exchange = await self.channel.declare_exchange(
                name=self.exchange_name,
                type=aio_pika.ExchangeType.FANOUT,
                durable=True
            )
            logger.info("✅ RabbitMQ Publisher Connected successfully.")
        except Exception as e:
            logger.error(f"❌ RabbitMQ Connection Error: {e}")
            raise e

    async def publish(self, payload: Dict[str, Any], routing_key: str = ""):
        """ارسال پیام به Exchange"""
        if not self.exchange:
            raise RuntimeError("RabbitMQ exchange is not initialized. Call connect() first.")

        message_body = json.dumps(payload, default=str).encode("utf-8")
        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # ماندگاری پیام در صورت ریستارت بروکر
            content_type="application/json"
        )

        await self.exchange.publish(message, routing_key=routing_key)

    async def close(self):
        """بستن اتصال هنگام خاموش شدن برنامه"""
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")


# ایجاد یک نمونه سراسری (Singleton)
mq_publisher = RabbitMQPublisher()
