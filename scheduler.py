import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# ایمپورت‌های پروژه شما
from core.config import settings
from modules.devices.models import Post
from modbus_client import ModbusReader
from modules.telemetry.schemas import TelemetryCreate
from modules.telemetry.service import TelemetryService

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ساخت انجین دیتابیس با استفاده از URL تنظیمات
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


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

                # ساخت نمونه از سرویس تله‌متری
                # (ارسال دیتا به وب‌سوکت باید داخل همین سرویس هندل شود)
                telemetry_service = TelemetryService(session)

                try:
                    # ثبت ولتاژ و ارسال
                    await telemetry_service.add_telemetry_data(TelemetryCreate(
                        post_id=device_id,
                        key="voltage",
                        value_float=float(voltage_val)
                    ))

                    # ثبت جریان و ارسال
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

                # غیرفعال کردن تجهیز اگر خطاها از حد مجاز گذشت
                max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
                if current_failures >= max_failures:
                    if getattr(device, 'is_active', True):
                        device.is_active = False
                        logger.error(
                            f"⚠️ Device ID {device_id} DEACTIVATED due to {current_failures} consecutive failures.")
                        # TODO: در صورت نیاز سرویس ارسال پیامک/نوتیفیکیشن قطعی به ادمین در اینجا فراخوانی شود

                session.add(device)
                await session.commit()

    async def poll_device(self, device_id: int, device_ip: str, polling_interval: int):
        reader = ModbusReader(host=device_ip)
        try:
            while self.is_running:
                try:
                    # فراخوانی متد خواندن دیتا (بدون آرگومان slave مطابق اصلاحات قبلی)
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
        """توقف تمامی تسک‌های تله‌متری"""
        logger.info("Stopping Telemetry Scheduler...")
        self.is_running = False
        for task in self._tasks:
            task.cancel()

        # منتظر ماندن برای لغو کامل تسک‌ها به صورت ایمن
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("All telemetry tasks stopped securely.")
