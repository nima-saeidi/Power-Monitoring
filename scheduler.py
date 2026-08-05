import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# ایمپورت‌های پروژه شما
from core.config import settings
from modules.devices.models import Post    # مطمئن شوید که فیلدهای consecutive_failures و is_active به این مدل اضافه شده‌اند
from modbus_client import ModbusReader

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

    async def handle_success(self, device_id: int, data):
        """عملیات پس از خواندن موفقیت‌آمیز داده‌ها"""
        async with AsyncSessionLocal() as session:
            device = await session.get(Post, device_id)
            if device:
                # اگر قبلا خطایی داشته صفر می‌شود
                if getattr(device, 'consecutive_failures', 0) > 0:
                    device.consecutive_failures = 0
                
                # TODO: ذخیره مقادیر data در دیتابیس (مثلاً در جدول TelemetryData)
                
                session.add(device)
                await session.commit()

    async def handle_failure(self, device_id: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز"""
        async with AsyncSessionLocal() as session:
            device = await session.get(Post, device_id)
            if device:
                # افزایش شمارنده خطا
                current_failures = getattr(device, 'consecutive_failures', 0) + 1
                device.consecutive_failures = current_failures
                
                logger.warning(f"Device ID {device_id} failed to respond. Failures: {current_failures} | Error: {error_msg}")

                # غیرفعال کردن تجهیز اگر خطاها از حد مجاز گذشت
                max_failures = getattr(settings, 'MAX_TELEMETRY_FAILURES', 3)
                if current_failures >= max_failures:
                    if getattr(device, 'is_active', True):
                        device.is_active = False
                        logger.error(f"⚠️ Device ID {device_id} DEACTIVATED due to {current_failures} consecutive failures.")
                        # (اختیاری) فراخوانی سرویس ارسال نوتیفیکیشن / پیامک به ادمین در اینجا
                
                session.add(device)
                await session.commit()

    async def poll_device(self, device_id: int, device_ip: str, polling_interval: int):
        """حلقه مداوم برای خواندن اطلاعات از یک تجهیز خاص"""
        reader = ModbusReader(host=device_ip)
        while self.is_running:
            try:
                # خواندن رجیسترها از تجهیز
                data = await reader.read_data(address=0, count=10)
                if data:
                    logger.info(f"Data from {device_ip} (ID: {device_id}): {data}")
                    await self.handle_success(device_id, data)
                else:
                    await self.handle_failure(device_id, "No data returned (Offline).")
            
            except Exception as e:
                await self.handle_failure(device_id, str(e))
            
            # زمان خواب بین هر بار خواندن بر اساس تنظیمات
            await asyncio.sleep(polling_interval)

    async def start(self):
        """شروع مانیتورینگ تمامی تجهیزات فعال"""
        self.is_running = True
        logger.info("Starting Telemetry Scheduler...")
        
        # باز کردن یک سشن فقط برای خواندن اولیه لیست تجهیزات فعال
        async with AsyncSessionLocal() as session:
            # واکشی تمام پست‌ها/تجهیزاتی که IP دارند و از نظر سیستمی فعال (is_active) هستند
            stmt = select(Post).where(Post.ip_address != None, Post.is_active == True)
            result = await session.execute(stmt)
            active_devices = result.scalars().all()

        interval = settings.POLLING_INTERVAL
        
        for dev in active_devices:
            # پاس دادن شناسه و IP به تسک مجزا
            task = asyncio.create_task(self.poll_device(dev.id, dev.ip_address, interval))
            self._tasks.append(task)
            logger.info(f"Scheduled task for Device ID {dev.id} at IP {dev.ip_address}")

    async def stop(self):
        """توقف تمامی تسک‌های تله‌متری"""
        logger.info("Stopping Telemetry Scheduler...")
        self.is_running = False
        for task in self._tasks:
            task.cancel()
        
        # منتظر ماندن برای لغو کامل تسک‌ها
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("All telemetry tasks stopped.")
