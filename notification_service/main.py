import asyncio
import json
import logging
import signal
import aio_pika
from core.config import settings
from modules.notifications.base import NotificationPayload, NotificationChannel
from modules.notifications.email_provider import EmailProvider
from modules.notifications.sms_provider import SMSProvider


logger = logging.getLogger("NotificationWorker")

email_provider = EmailProvider()
sms_provider = SMSProvider()


async def process_notification(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            body_data = json.loads(message.body.decode("utf-8"))
            payload = NotificationPayload(**body_data)
            logger.info(f"📥 Received task: [{payload.title}] | Channel: {payload.channel.value}")

            tasks = []

            # ارسال ایمیل
            if payload.channel in (NotificationChannel.EMAIL, NotificationChannel.ALL):
                if payload.email_addresses:
                    tasks.append(
                        email_provider.send(
                            to_emails=[str(e) for e in payload.email_addresses],
                            subject=payload.title,
                            body=payload.message
                        )
                    )

            # ارسال پیامک
            if payload.channel in (NotificationChannel.SMS, NotificationChannel.ALL):
                if payload.phone_numbers:
                    sms_text = f"{payload.title}\n{payload.message}"
                    tasks.append(
                        sms_provider.send(
                            phone_numbers=payload.phone_numbers,
                            message=sms_text
                        )
                    )

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.error(f"Error during notification execution: {res}")
            else:
                logger.warning("No destinations matched for payload.")

        except json.JSONDecodeError:
            logger.error("Failed to decode message body as JSON.")
        except Exception as e:
            logger.error(f"Unexpected error while processing message: {e}", exc_info=True)


async def main():
    logger.info("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue(
        settings.RABBITMQ_NOTIFICATION_QUEUE,
        durable=True
    )

    logger.info(f"🚀 Notification Worker started. Consuming from queue: '{settings.RABBITMQ_NOTIFICATION_QUEUE}'")
    await queue.consume(process_notification)

    # مدیریت خاموش‌سازی تمیز (Graceful Shutdown)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    logger.info("🛑 Shutting down Notification Worker...")
    await connection.close()
    logger.info("Connection closed successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped manually.")
