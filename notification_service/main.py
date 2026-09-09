import asyncio
import json
import logging
import aio_pika
from core.config import settings
from modules.notifications.schemas import NotificationPayload, NotificationChannel
from modules.notifications.email_provider import EmailProvider
from modules.notifications.sms_provider import SMSProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NotificationService")


class NotificationWorker:
    def __init__(self):
        self.email_provider = EmailProvider()
        self.sms_provider = SMSProvider()

    async def process_notification(self, payload: NotificationPayload):
        tasks = []

        if payload.channel in [NotificationChannel.EMAIL, NotificationChannel.ALL]:
            if payload.email_addresses:
                tasks.append(self.email_provider.send_email(
                    payload.email_addresses, payload.title, payload.message
                ))

        if payload.channel in [NotificationChannel.SMS, NotificationChannel.ALL]:
            if payload.phone_numbers:
                tasks.append(self.sms_provider.send_sms(
                    payload.phone_numbers, payload.message
                ))

        if tasks:
            await asyncio.gather(*tasks)

    async def consume(self):
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # تعریف صف
            queue = await channel.declare_queue(
                settings.RABBITMQ_NOTIFICATION_QUEUE, durable=True
            )

            logger.info("[*] Waiting for notification messages. To exit press CTRL+C")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            data = json.loads(message.body.decode())
                            payload = NotificationPayload(**data)
                            logger.info(f"Received notification: {payload.title}")
                            await self.process_notification(payload)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    worker = NotificationWorker()
    try:
        asyncio.run(worker.consume())
    except KeyboardInterrupt:
        print("Service stopped.")
