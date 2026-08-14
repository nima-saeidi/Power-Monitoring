import asyncio
import logging
import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from datetime import datetime, timezone

# ایمپورت‌های پروژه شما
from core.config import settings
from modules.devices.models import Post
from telemetry_service.modbus_client import ModbusReader
from modules.telemetry.schemas import TelemetryCreate
from modules.telemetry.service import TelemetryService

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ساخت انجین دیتابیس با استفاده از URL تنظیمات
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# اتصال به ردیس (خواندن از تنظیمات، با مقدار پیش‌فرض داکر)
REDIS_URL = getattr(settings, 'REDIS_URL', "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class TelemetryScheduler:
    def __init__(self):
        self.is_running = False
        self._tasks = []

    async def handle_success(self, device_id: int, data: list):
        """عملیات پس از خواندن موفقیت‌آمیز داده‌ها"""
        async with AsyncSessionLocal() as session:
            device = await session.get(Post, device_id)
            if device:
                # ریست کردن شمارنده خطا در صورت موفقیت
                if getattr(device, 'consecutive_failures', 0) > 0:
                    device.consecutive_failures = 0
                    session.add(device)

                # استخراج دیتا (بر اساس پیکربندی آدرس رجیسترهای Modbus شما)
                voltage_val = data[0] if len(data) > 0 else 0.0
                current_val = data[1] if len(data) > 1 else 0.0

                # ---------------------------------------------------------
                # ۱. انتشار آنی داده‌ها در Redis (برای ارسال به فرانت‌اند از طریق Core)
                # ---------------------------------------------------------
                try:
                    live_payload = {
                        "post_id": device_id,
                        "voltage": float(voltage_val),
                        "current": float(current_val),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    # انتشار پیام در کانال live_power_data
                    await redis_client.publish("live_power_data", json.dumps(live_payload))
                except Exception as e:
                    logger.error(f"Redis publish error for device {device_id}: {e}")

                # ---------------------------------------------------------
                # ۲. ذخیره داده‌ها در دیتابیس تله‌متری (Timeseries)
                # ---------------------------------------------------------
                telemetry_service = TelemetryService(session)

                try:
                    # ثبت ولتاژ
                    await telemetry_service.add_telemetry_data(TelemetryCreate(
                        post_id=device_id,
                        key="voltage",
                        value_float=float(voltage_val)
                    ))

                    # ثبت جریان
                    await telemetry_service.add_telemetry_data(TelemetryCreate(
                        post_id=device_id,
                        key="current",
                        value_float=float(current_val)
                    ))

                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error saving telemetry data for device {device_id}: {e}")

    async def handle_failure(self, device_id: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز"""
        async with AsyncSessionLocal() as session:
            device = await session.get(Post, device_id)
            if device:
                # افزایش شمارنده خطا
                current_failures = getattr(device, 'consecutive_failures', 0) + 1
                device.consecutive_failures = current_failures

                logger.warning(
                    f"Device ID {device_id} failed to respond. Failures: {current_failures} | Error: {error_msg}")

                # انتشار هشدار قطعی تجهیز به داشبورد
                try:
                    alert_payload = {
                        "post_id": device_id,
                        "status": "offline",
                        "failures": current_failures,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await redis_client.publish("device_alerts", json.dumps(alert_payload))
                except Exception:
                    pass

                # غیرفعال کردن تجهیز اگر خطاها از حد مجاز گذشت
                max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
                if current_failures >= max_failures:
                    if getattr(device, 'is_active', True):
                        device.is_active = False
                        logger.error(
                            f"⚠️ Device ID {device_id} DEACTIVATED due to {current_failures} consecutive failures.")

                        # انتشار هشدار غیرفعال شدن (Critical)
                        try:
                            await redis_client.publish("device_alerts", json.dumps({
                                "post_id": device_id,
                                "status": "deactivated",
                                "reason": "max_failures_reached",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }))
                        except Exception:
                            pass

                        # TODO: در صورت نیاز سرویس ارسال پیامک/نوتیفیکیشن قطعی به ادمین در اینجا فراخوانی شود

                session.add(device)
                await session.commit()

    async def poll_device(self, device_id: int, device_ip: str, polling_interval: int):
        reader = ModbusReader(host=device_ip)
        try:
            while self.is_running:
                try:
                    # فراخوانی متد خواندن دیتا
                    data = await reader.read_data(address=0, count=10)
                    if data:
                        await self.handle_success(device_id, data)
                    else:
                        await self.handle_failure(device_id, "No data returned (Offline).")
                except Exception as e:
                    await self.handle_failure(device_id, f"Modbus Read Error: {str(e)}")

                await asyncio.sleep(polling_interval)
        finally:
            # بستن کانکشن Modbus هنگام توقف تسک
            if hasattr(reader, 'close'):
                await reader.close()

    async def start(self):
        """شروع مانیتورینگ تمامی تجهیزات فعال"""
        self.is_running = True
        logger.info("Starting Telemetry Scheduler...")

        # باز کردن یک سشن برای خواندن اولیه لیست تجهیزات فعال
        async with AsyncSessionLocal() as session:
            stmt = select(Post).where(Post.ip_address.isnot(None), Post.is_active == True)
            result = await session.execute(stmt)
            active_devices = result.scalars().all()

        interval = getattr(settings, 'POLLING_INTERVAL', 5)  # پیش‌فرض ۵ ثانیه

        for dev in active_devices:
            task = asyncio.create_task(self.poll_device(dev.id, dev.ip_address, interval))
            self._tasks.append(task)
            logger.info(f"Scheduled task for Device ID {dev.id} at IP {dev.ip_address} with {interval}s interval.")

    async def stop(self):
        """توقف تمامی تسک‌های تله‌متری و اتصالات"""
        logger.info("Stopping Telemetry Scheduler...")
        self.is_running = False
        for task in self._tasks:
            task.cancel()

        # منتظر ماندن برای لغو کامل تسک‌ها به صورت ایمن
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # بستن کانکشن ردیس
        try:
            # در نسخه‌های جدید redis.asyncio متد aclose استفاده می‌شود
            if hasattr(redis_client, 'aclose'):
                await redis_client.aclose()
            else:
                await redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

        logger.info("All telemetry tasks and connections stopped securely.")
