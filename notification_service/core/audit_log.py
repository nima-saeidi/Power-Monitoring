import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import aio_pika

logger = logging.getLogger("NotificationWorker.AuditLog")

LOGS_QUEUE_NAME = "logs_queue"


async def send_service_log(
        channel: aio_pika.abc.AbstractChannel,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
        service_name: str = "notification_service",
) -> None:
    """
    ارسال یک رویداد لاگ به صف logs_queue با همان ساختار LogCreate که
    logging_service مصرف می‌کند (سرویس لاگ مرکزی). این تابع از همان کانال
    فعال RabbitMQ که ورکر نوتیفیکیشن برای مصرف پیام‌ها استفاده می‌کند بهره
    می‌برد تا اتصال جدیدی باز نشود.
    """
    try:
        message_body = {
            "service_name": service_name,
            "action": action,
            "user_id": user_id,
            "details": {**details, "timestamp": datetime.now(timezone.utc).isoformat()},
        }
        message = aio_pika.Message(
            body=json.dumps(message_body, default=str).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await channel.default_exchange.publish(message, routing_key=LOGS_QUEUE_NAME)
    except Exception as e:
        logger.error(f"Failed to publish audit log '{action}' to logs_queue: {e}")
