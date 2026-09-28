import asyncio
import functools
import json
import logging
import signal
import aio_pika
from core.config import settings
from core.audit_log import send_service_log
from modules.notifications.base import NotificationPayload, NotificationChannel
from modules.notifications.email_provider import EmailProvider
from modules.notifications.sms_provider import SMSProvider


logger = logging.getLogger("NotificationWorker")

email_provider = EmailProvider()
sms_provider = SMSProvider()


class NotificationDeliveryError(Exception):
    """Raised when every dispatched channel for a notification failed to send,
    even after the provider's own internal retries. Without this, a transient
    SMTP/SMS outage would be logged as *_FAILED and the message would still be
    ack'd away for good - the DLQ (and scripts/dlq_tool.py replay) only ever
    catches processing crashes, never delivery failures, unless this is raised."""


async def process_notification(message: aio_pika.IncomingMessage, channel: aio_pika.abc.AbstractChannel) -> None:
    async with message.process(requeue=False):
        try:
            body_data = json.loads(message.body.decode("utf-8"))
            payload = NotificationPayload(**body_data)
            logger.info(f"📥 Received task: [{payload.title}] | Channel: {payload.channel.value}")

            channels_dispatched = []

            if payload.channel in (NotificationChannel.EMAIL, NotificationChannel.ALL):
                if payload.email_addresses:
                    channels_dispatched.append((
                        "email",
                        [str(e) for e in payload.email_addresses],
                        email_provider.send(
                            to_emails=[str(e) for e in payload.email_addresses],
                            subject=payload.title,
                            body=payload.message,
                            html_body=payload.html_message
                        )
                    ))

            if payload.channel in (NotificationChannel.SMS, NotificationChannel.ALL):
                if payload.phone_numbers:
                    sms_text = f"{payload.title}\n{payload.message}"
                    channels_dispatched.append((
                        "sms",
                        payload.phone_numbers,
                        sms_provider.send(
                            phone_numbers=payload.phone_numbers,
                            message=sms_text
                        )
                    ))

            if channels_dispatched:
                results = await asyncio.gather(
                    *(task for _, _, task in channels_dispatched), return_exceptions=True
                )
                failed_channels = []
                for (channel_name, recipients, _), res in zip(channels_dispatched, results):
                    if isinstance(res, Exception):
                        logger.error(f"Error during {channel_name} notification execution: {res}")
                        await send_service_log(
                            channel, action=f"NOTIFICATION_{channel_name.upper()}_FAILED",
                            details={
                                "success": False, "severity": "ERROR",
                                "title": payload.title, "recipients": recipients,
                                "error_message": str(res),
                            }
                        )
                        failed_channels.append(channel_name)
                    else:
                        success = bool(res)
                        await send_service_log(
                            channel,
                            action=f"NOTIFICATION_{channel_name.upper()}_SENT" if success
                            else f"NOTIFICATION_{channel_name.upper()}_FAILED",
                            details={
                                "success": success, "severity": "INFO" if success else "WARNING",
                                "title": payload.title, "recipients": recipients,
                            }
                        )
                        if not success:
                            failed_channels.append(channel_name)

                if failed_channels:
                    # Every *_FAILED log above is already written - raise so
                    # message.process(requeue=False) dead-letters this message
                    # instead of ack-ing a failed delivery away for good.
                    raise NotificationDeliveryError(
                        f"Delivery failed on: {', '.join(failed_channels)}"
                    )
            else:
                logger.warning("No destinations matched for payload.")
                await send_service_log(
                    channel, action="NOTIFICATION_NO_DESTINATION",
                    details={
                        "success": False, "severity": "WARNING",
                        "title": payload.title, "channel": payload.channel.value,
                    }
                )

        except json.JSONDecodeError:
            logger.error("Failed to decode message body as JSON.")
            await send_service_log(
                channel, action="NOTIFICATION_INVALID_PAYLOAD",
                details={"success": False, "severity": "ERROR", "raw_body": message.body.decode("utf-8", errors="ignore")}
            )
            raise
        except NotificationDeliveryError:
            # Per-channel failure already logged above; just dead-letter.
            raise
        except Exception as e:
            logger.error(f"Unexpected error while processing message: {e}", exc_info=True)
            await send_service_log(
                channel, action="NOTIFICATION_PROCESSING_ERROR",
                details={"success": False, "severity": "CRITICAL", "error_message": str(e)}
            )
            raise


async def _declare_queue_with_dlq(connection, channel, queue_name: str, prefetch: int = 10):
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
        logger.error(
            f"Queue '{queue_name}' already exists with incompatible arguments. "
            "Falling back WITHOUT dead-letter support; delete the queue manually once to enable DLQ."
        )
        fresh_channel = await connection.channel()
        await fresh_channel.set_qos(prefetch_count=prefetch)
        queue = await fresh_channel.declare_queue(queue_name, durable=True)
        return queue, fresh_channel


async def main():
    # Fail loud at boot rather than silent on the first real alert: a bad
    # SMTP password or unreachable host would otherwise only ever show up as
    # a per-message WARNING buried in the logs, indistinguishable from "no
    # emails were queued yet".
    await email_provider.check_connection()
    if not settings.SMS_API_KEY:
        logger.warning("⚠️ SMS_API_KEY is not configured. All outgoing SMS will be silently skipped.")

    logger.info("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    queue, channel = await _declare_queue_with_dlq(connection, channel, settings.RABBITMQ_NOTIFICATION_QUEUE)

    _, channel = await _declare_queue_with_dlq(connection, channel, "logs_queue")

    logger.info(f"🚀 Notification Worker started. Consuming from queue: '{settings.RABBITMQ_NOTIFICATION_QUEUE}'")
    await queue.consume(functools.partial(process_notification, channel=channel))

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
