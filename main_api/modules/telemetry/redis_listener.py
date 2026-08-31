import asyncio
import json
import logging
import redis.asyncio as redis

from main_api.core.config import settings
from main_api.modules.telemetry.ws_manager import ws_manager

logger = logging.getLogger(__name__)


async def listen_to_redis_and_save():
    """
    تسک پس‌زمینه برای اشتراک در کانال Redis و ارسال پیام‌های تله‌متری به کلاینت‌های WebSocket
    """
    logger.info("Starting Redis Telemetry Listener...")
    while True:
        try:
            # اتصال به ردیس با استفاده از تنظیمات سراسری پروژه
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe("telemetry_stream")
            logger.info("📡 Subscribed to Redis channel: telemetry_stream")

            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    if raw_data:
                        try:
                            payload = json.loads(raw_data)
                            # پخش زنده داده برای تمام فرانت‌اندها و کلاینت‌های متصل
                            await ws_manager.broadcast(payload)
                        except json.JSONDecodeError:
                            logger.warning(f"Malformed JSON received from Redis: {raw_data}")

        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled successfully.")
            break
        except Exception as e:
            logger.error(f"Redis listener error: {e}. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
