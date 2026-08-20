import asyncio
import logging
import json
import httpx
import redis.asyncio as redis
from datetime import datetime, timezone

# ایمپورت‌های پروژه
from core.config import settings
from modules.telemetry.modbus_client import ModbusReader

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# گرفتن آدرس ردیس از تنظیمات
REDIS_URL = getattr(settings, 'REDIS_URL', "redis://127.0.0.1:6379/0")

# تعریف کلاینت ردیس با مدیریت خطا برای محیط تست
try:
    redis_client = redis.from_url(
        "redis://127.0.0.1:6379",
        protocol=2  # <--- این پارامتر خطای HELLO 3 را رفع می‌کند
    )
except Exception as e:
    logger.warning(f"⚠️ Redis init error: {e}. Running in WITHOUT-REDIS mode.")
    redis_client = None


class TelemetryScheduler:
    def __init__(self):
        self.is_running = False
        self._tasks = []

    async def handle_success(self, feeder_id: int, data: list):
        """عملیات پس از خواندن موفقیت‌آمیز داده‌ها (فقط پابلیش در ردیس)"""

        voltage_val = data[0] if len(data) > 0 else 0.0
        current_val = data[1] if len(data) > 1 else 0.0
        active_power = data[2] if len(data) > 2 else 0.0  # اضافه شدن اکتیو پاور بر اساس لیسنر main_api

        # لاگ کردن دیتا
        logger.info(f"📊 Feeder {feeder_id} Data - V: {voltage_val}, I: {current_val}, P: {active_power}")

        if redis_client:
            try:
                live_payload = {
                    "feeder_id": feeder_id,
                    "voltage": float(voltage_val),
                    "current": float(current_val),
                    "active_power": float(active_power),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await redis_client.publish("live_power_data", json.dumps(live_payload))
            except Exception as e:
                logger.error(f"Redis publish error for feeder {feeder_id}: {e}")

    async def handle_failure(self, feeder_id: int, current_failures: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز (ارسال آلرت به ردیس)"""

        logger.warning(
            f"Feeder ID {feeder_id} failed to respond. Failures: {current_failures} | Error: {error_msg}")

        if redis_client:
            max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
            # اگر تعداد خطاها از حد مجاز بگذرد وضعیت deactivated ارسال می‌شود تا main_api فیدر را در دیتابیس غیرفعال کند
            status = "deactivated" if current_failures >= max_failures else "offline"

            try:
                alert_payload = {
                    "feeder_id": feeder_id,
                    "status": status,
                    "failures": current_failures,
                    "reason": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await redis_client.publish("device_alerts", json.dumps(alert_payload))
            except Exception:
                pass

    async def poll_device(self, feeder_id: int, device_ip: str, port: int, modbus_address: int, polling_interval: int):
        """پایش مداوم یک فیدر خاص"""
        reader = ModbusReader(host=device_ip, port=port)  # ارسال port به کلاینت مدباس
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
                        await self.handle_failure(feeder_id, current_fails, "No data returned (Offline).")
                except Exception as e:
                    current_fails += 1
                    await self.handle_failure(feeder_id, current_fails, f"Modbus Read Error: {str(e)}")

                # اگر فیدر قطع است، زمان انتظار را بیشتر کن (بک‌اف ۶۰ ثانیه‌ای لوکال)
                if current_fails >= max_failures:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(polling_interval)
        finally:
            if hasattr(reader, 'close'):
                await reader.close()

    async def get_active_feeders_from_api(self):
        """دریافت لیست فیدرها از main_api به جای دیتابیس"""
        main_api_url = getattr(settings, 'MAIN_API_URL', "http://127.0.0.1:8000")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{main_api_url}/api/v1/telemetry/active-feeders", timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to fetch feeders. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Cannot connect to main_api for feeders list: {e}")
        return []

    async def start(self):
        """شروع مانیتورینگ تمامی فیدرها"""
        self.is_running = True
        logger.info("Starting Pure Worker Telemetry Scheduler...")

        # واکشی اطلاعات فیدرها از طریق API به جای دیتابیس لوکال
        active_feeders = await self.get_active_feeders_from_api()

        if not active_feeders:
            logger.warning("No active feeders found or main_api is unreachable. Worker is idle.")

        interval = getattr(settings, 'POLLING_INTERVAL', 5)

        for feeder in active_feeders:
            feeder_id = feeder.get("id")
            ip = feeder.get("ip_address")
            port = feeder.get("port", 502)  # خواندن پورت از ریسپانس API (پیش‌فرض 502)
            modbus_addr = feeder.get("modbus_address", 1)

            if feeder_id and ip:
                task = asyncio.create_task(self.poll_device(feeder_id, ip, port, modbus_addr, interval))
                self._tasks.append(task)
                logger.info(
                    f"Scheduled task for Feeder ID {feeder_id} at Post {ip}:{port} (Modbus ID: {modbus_addr}) with {interval}s interval."
                )

    async def stop(self):
        """توقف تمامی تسک‌های تله‌متری"""
        logger.info("Stopping Telemetry Scheduler...")
        self.is_running = False
        for task in self._tasks:
            task.cancel()

        if self._tasks:
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
