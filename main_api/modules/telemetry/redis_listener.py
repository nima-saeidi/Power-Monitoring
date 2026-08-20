import asyncio
import json
import logging
import redis.asyncio as redis
from main_api.core.database import AsyncSessionLocal
from main_api.modules.telemetry.schemas import TelemetryCreate
from main_api.modules.telemetry.service import TelemetryService
from main_api.core.config import settings

# from core.websockets import manager as ws_manager  # در صورت پیاده‌سازی وب‌سوکت برای فرانت‌اند

logger = logging.getLogger(__name__)


async def listen_to_redis_and_save():
    """این تابع به صورت مداوم به ردیس گوش می‌دهد و داده‌ها را در دیتابیس ذخیره می‌کند"""
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, protocol=2)
    pubsub = redis_client.pubsub()

    # مشترک شدن در کانالی که تله‌متری دیتا را می‌فرستد
    await pubsub.subscribe("live_power_data")
    logger.info("📡 Subscribed to Redis channel: live_power_data")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # ۱. دریافت و تبدیل دیتا
                    raw_data = json.loads(message["data"])

                    # تبدیل post_id و feeder_id به int (طبق مدل TelemetryBase)
                    feeder_id = raw_data.get("feeder_id")
                    feeder_id = int(feeder_id) if feeder_id is not None else None

                    post_id = raw_data.get("post_id")
                    post_id = int(post_id) if post_id is not None else None

                    voltage = raw_data.get("voltage")
                    current = raw_data.get("current")
                    active_power = raw_data.get("active_power")

                    # ۲. باز کردن سشن دیتابیس
                    async with AsyncSessionLocal() as db_session:
                        service = TelemetryService(db_session)

                        # ۳. ذخیره ولتاژ در فیلد value_int
                        if voltage is not None:
                            await service.add_telemetry_data(TelemetryCreate(
                                feeder_id=feeder_id,
                                post_id=post_id,
                                key="voltage",
                                value_int=int(float(voltage))  # 👈 استفاده از value_int و تبدیل به صحیح
                            ))

                        # ۴. ذخیره جریان در فیلد value_int
                        if current is not None:
                            await service.add_telemetry_data(TelemetryCreate(
                                feeder_id=feeder_id,
                                post_id=post_id,
                                key="current",
                                value_int=int(float(current))  # 👈 استفاده از value_int
                            ))

                        # ۵. ذخیره توان اکتیو در فیلد value_int
                        if active_power is not None:
                            await service.add_telemetry_data(TelemetryCreate(
                                feeder_id=feeder_id,
                                post_id=post_id,
                                key="active_power",
                                value_int=int(float(active_power))  # 👈 استفاده از value_int
                            ))

                        # کامیت کردن تغییرات در دیتابیس
                        await db_session.commit()
                        logger.info(f"✅ Telemetry saved for Feeder {feeder_id} - V:{voltage}, I:{current}")

                        # ۶. (اختیاری) برادکست دیتا برای داشبورد React از طریق وب‌سوکت
                        # await ws_manager.broadcast_json(raw_data)

                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON format received: {message['data']}")
                except ValueError as ve:
                    # در صورتی که دیتای دریافتی قابل تبدیل به عدد صحیح نباشد
                    logger.error(f"❌ Error converting value to int: {str(ve)} - Data: {message['data']}")
                except Exception as e:
                    logger.error(f"❌ Error processing message: {str(e)}")

    except asyncio.CancelledError:
        logger.info("🛑 Redis listener task was cancelled (App shutting down).")
    except Exception as e:
        logger.critical(f"💥 Critical error in Redis listener loop: {str(e)}")
    finally:
        await pubsub.unsubscribe("live_power_data")
        await redis_client.aclose()
        logger.info("🔌 Redis connection closed safely.")
