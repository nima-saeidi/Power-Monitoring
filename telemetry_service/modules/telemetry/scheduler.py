import asyncio
import json
import logging
from datetime import datetime, timezone
import httpx

# ایمپورت‌های پروژه
from core.config import settings
from modules.telemetry.modbus_client import ModbusReader
from modules.telemetry.schemas import TelemetryCreate, DeviceAlertSchema
from modules.telemetry.service import TelemetryService

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelemetryScheduler:
    def __init__(self):
        self.is_running = False
        self._tasks: list[asyncio.Task] = []

    async def handle_success(self, feeder_id: int, data: list):
        """پردازش و تفکیک ۵ پارامتر الکتریکی: فقط ذخیره در دیتابیس سری‌زمانی"""
        active_power_val = float(data[0]) if len(data) > 0 else 0.0
        reactive_power_val = float(data[1]) if len(data) > 1 else 0.0
        voltage_val = float(data[2]) if len(data) > 2 else 0.0
        current_val = float(data[3]) if len(data) > 3 else 0.0
        power_factor_val = float(data[4]) if len(data) > 4 else 0.0

        logger.info(
            f"📊 Feeder {feeder_id} Data | "
            f"Active Power: {active_power_val:.2f} W, "
            f"Reactive Power: {reactive_power_val:.2f} VAr, "
            f"Voltage: {voltage_val:.2f} V, "
            f"Current: {current_val:.2f} A, "
            f"Power Factor: {power_factor_val:.2f}"
        )

        telemetry_in = TelemetryCreate(
            feeder_id=feeder_id,
            active_power=active_power_val,
            reactive_power=reactive_power_val,
            voltage=voltage_val,
            current=current_val,
            power_factor=power_factor_val,
            timestamp=datetime.now(timezone.utc)
        )

        # ذخیره در دیتابیس (بدون ارسال ردیس)
        await TelemetryService.process_and_store(telemetry_in)

    async def handle_failure(self, feeder_id: int, current_failures: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز (ثبت در لاگ)"""
        logger.warning(
            f"⚠️ Feeder ID {feeder_id} failed to respond. Failures: {current_failures} | Error: {error_msg}"
        )

        # در صورت نیاز به ارسال آلرت به RabbitMQ به جای Redis، می‌توانید لاجیک انتشار پیام را در آینده اینجا اضافه کنید.

    async def poll_device(
            self, feeder_id: int, device_ip: str, port: int, modbus_address: int, polling_interval: int
    ):
        """پایش مداوم یک فیدر با مودباس (خواندن ۵ پارامتر اول)"""
        reader = ModbusReader(host=device_ip, port=port)
        max_failures = getattr(settings, "MAX_TELEMETRY_FAILURES", 3)
        current_fails = 0

        try:
            while self.is_running:
                try:
                    # تغییر count از ۱۰ به ۵ برای بهبود سرعت شبکه و خواندن تنها پارامترهای ضروری
                    data = await reader.read_data(address=0, count=5, slave=modbus_address)
                    if data:
                        current_fails = 0
                        await self.handle_success(feeder_id, data)
                    else:
                        current_fails += 1
                        await self.handle_failure(feeder_id, current_fails, "No data returned (Offline).")
                except Exception as e:
                    current_fails += 1
                    await self.handle_failure(feeder_id, current_fails, f"Modbus Read Error: {str(e)}")

                # بک‌اف در صورت قطعی مکرر
                if current_fails >= max_failures:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(polling_interval)
        finally:
            if hasattr(reader, "close"):
                await reader.close()

    async def get_active_feeders_from_api(self) -> list[dict]:
        """واکشی لیست فیدرهای فعال از main_api"""
        main_api_url = getattr(settings, "MAIN_API_URL", "http://127.0.0.1:8000").rstrip("/")
        url = f"{main_api_url}/telemetry/active-feeders"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                logger.error(
                    f"Failed to fetch feeders. URL: {url} | Status: {response.status_code} | Body: {response.text}"
                )
        except Exception as e:
            logger.error(f"Cannot connect to main_api at {url}: {e}")
        return []

    async def start(self):
        """راه‌اندازی وظایف پایش برای تمامی فیدرهای فعال"""
        self.is_running = True
        logger.info("🚀 Starting Pure Worker Telemetry Scheduler...")

        active_feeders = await self.get_active_feeders_from_api()
        if not active_feeders:
            logger.warning("⚠️ No active feeders found or main_api is unreachable. Worker is idle.")

        interval = getattr(settings, "POLLING_INTERVAL", 300)

        for feeder in active_feeders:
            feeder_id = feeder.get("id")
            ip = feeder.get("ip_address")
            port = feeder.get("port", 502)
            modbus_addr = feeder.get("modbus_address", 1)

            if feeder_id and ip:
                task = asyncio.create_task(
                    self.poll_device(feeder_id, ip, port, modbus_addr, interval)
                )
                self._tasks.append(task)
                logger.info(
                    f"Scheduled monitor for Feeder ID {feeder_id} at {ip}:{port} (Modbus ID: {modbus_addr}) every {interval}s."
                )

    async def stop(self):
        """توقف ایمن تسک‌ها"""
        logger.info("🛑 Stopping Telemetry Scheduler...")
        self.is_running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info("All telemetry scheduler tasks and connections stopped cleanly.")
