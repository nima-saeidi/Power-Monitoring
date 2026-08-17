import asyncio
import logging
import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone

# ایمپورت‌های پروژه
from core.config import settings
from telemetry_service.modules.telemetry.local_models import LocalFeeder, LocalPost
from telemetry_service.modbus_client import ModbusReader

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

CACHE_URL = getattr(settings, 'REDIS_URL', "redis://127.0.0.1:6379/0")

# تعریف کلاینت ردیس با مدیریت خطا برای محیط تست
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.warning(f"⚠️ Redis init error: {e}. Running in WITHOUT-REDIS mode.")
    redis_client = None


class TelemetryScheduler:
    def __init__(self):
        self.is_running = False
        self._tasks = []

    async def handle_success(self, feeder_id: int, data: list):
        """عملیات پس از خواندن موفقیت‌آمیز داده‌ها"""
        async with AsyncSessionLocal() as session:
            feeder = await session.get(LocalFeeder, feeder_id)
            if feeder:
                needs_update = False

                # ریست کردن شمارنده خطا در صورت موفقیت
                if getattr(feeder, 'consecutive_failures', 0) > 0:
                    feeder.consecutive_failures = 0
                    needs_update = True

                # فعال‌سازی مجدد فیدر در صورت اتصال دوباره
                if getattr(feeder, 'is_active', True) is False:
                    feeder.is_active = True
                    needs_update = True
                    logger.info(f"✅ Feeder ID {feeder_id} REACTIVATED successfully.")

                if needs_update:
                    session.add(feeder)
                    await session.commit()

                # استخراج دیتا
                voltage_val = data[0] if len(data) > 0 else 0.0
                current_val = data[1] if len(data) > 1 else 0.0

                # لاگ کردن دیتا برای تست بدون ردیس
                logger.info(f"📊 Feeder {feeder_id} Data - V: {voltage_val}, I: {current_val}")

                if redis_client:
                    try:
                        live_payload = {
                            "feeder_id": feeder_id,
                            "voltage": float(voltage_val),
                            "current": float(current_val),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await redis_client.publish("live_power_data", json.dumps(live_payload))
                    except Exception as e:
                        logger.error(f"Redis publish error for feeder {feeder_id}: {e}")

    async def handle_failure(self, feeder_id: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز"""
        async with AsyncSessionLocal() as session:
            feeder = await session.get(LocalFeeder, feeder_id)
            if feeder:
                current_failures = getattr(feeder, 'consecutive_failures', 0) + 1
                feeder.consecutive_failures = current_failures

                logger.warning(
                    f"Feeder ID {feeder_id} failed to respond. Failures: {current_failures} | Error: {error_msg}")

                if redis_client:
                    try:
                        alert_payload = {
                            "feeder_id": feeder_id,
                            "status": "offline",
                            "failures": current_failures,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await redis_client.publish("device_alerts", json.dumps(alert_payload))
                    except Exception:
                        pass

                max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
                if current_failures >= max_failures:
                    if getattr(feeder, 'is_active', True):
                        feeder.is_active = False
                        logger.error(
                            f"⚠️ Feeder ID {feeder_id} DEACTIVATED due to {current_failures} consecutive failures.")

                        if redis_client:
                            try:
                                await redis_client.publish("device_alerts", json.dumps({
                                    "feeder_id": feeder_id,
                                    "status": "deactivated",
                                    "reason": "max_failures_reached",
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }))
                            except Exception:
                                pass

                session.add(feeder)
                await session.commit()

    async def poll_device(self, feeder_id: int, device_ip: str, modbus_address: int, polling_interval: int):
        reader = ModbusReader(host=device_ip)
        max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
        current_fails = 0

        try:
            while self.is_running:
                try:
                    data = await reader.read_data(address=0, count=10, slave=modbus_address)
                    if data:
                        current_fails = 0
                        await self.handle_success(feeder_id, data)
                    else:
                        current_fails += 1
                        await self.handle_failure(feeder_id, "No data returned (Offline).")
                except Exception as e:
                    current_fails += 1
                    await self.handle_failure(feeder_id, f"Modbus Read Error: {str(e)}")

                # اگر فیدر قطع است، زمان انتظار را بیشتر کن (بک‌اف ۶۰ ثانیه‌ای)
                if current_fails >= max_failures:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(polling_interval)
        finally:
            if hasattr(reader, 'close'):
                await reader.close()

    async def start(self):
        """شروع مانیتورینگ تمامی فیدرها"""
        self.is_running = True
        logger.info("Starting Telemetry Scheduler for Feeders...")

        async with AsyncSessionLocal() as session:
            stmt = (
                select(LocalFeeder)
                .options(joinedload(LocalFeeder.post))
                .join(LocalPost)
                .where(
                    LocalPost.is_active == True,
                    LocalPost.ip_address.isnot(None)
                )
            )
            result = await session.execute(stmt)
            all_feeders = result.scalars().all()

        interval = getattr(settings, 'POLLING_INTERVAL', 5)

        for feeder in all_feeders:
            ip = feeder.post.ip_address
            modbus_addr = feeder.modbus_address or 1

            task = asyncio.create_task(self.poll_device(feeder.id, ip, modbus_addr, interval))
            self._tasks.append(task)
            logger.info(
                f"Scheduled task for Feeder ID {feeder.id} at Post IP {ip} (Modbus ID: {modbus_addr}) with {interval}s interval.")

    async def stop(self):
        """توقف تمامی تسک‌های تله‌متری"""
        logger.info("Stopping Telemetry Scheduler...")
        self.is_running = False
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        if redis_client:
            try:
                if hasattr(redis_client, 'aclose'):
                    await redis_client.aclose()
                else:
                    await redis_client.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        logger.info("All telemetry tasks and connections stopped securely.")
