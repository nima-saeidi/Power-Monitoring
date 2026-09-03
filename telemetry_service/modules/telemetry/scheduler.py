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
        # ذخیره تسک‌ها به همراه کانفیگ آن‌ها بر اساس feeder_id
        self._tasks: dict[int, asyncio.Task] = {}
        self._task_configs: dict[int, dict] = {}
        self._sync_task: asyncio.Task | None = None

    async def handle_success(self, feeder_id: int, values: dict):
        """پردازش و تفکیک ۵ پارامتر الکتریکی خوانده شده از رجیسترهای داینامیک و ذخیره در دیتابیس"""
        active_power_val = float(values.get('active_power', 0.0))
        reactive_power_val = float(values.get('reactive_power', 0.0))
        voltage_val = float(values.get('voltage', 0.0))
        current_val = float(values.get('current', 0.0))
        power_factor_val = float(values.get('power_factor', 0.0))

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

        await TelemetryService.process_and_store(telemetry_in)

    async def handle_failure(self, feeder_id: int, current_failures: int, error_msg: str):
        """عملیات در صورت عدم پاسخگویی تجهیز"""
        logger.warning(
            f"⚠️ Feeder ID {feeder_id} failed to respond. Failures: {current_failures} | Error: {error_msg}"
        )

    async def poll_device(
        self, feeder_id: int, device_ip: str, port: int, modbus_address: int, polling_interval: int, registers: dict
    ):
        """پایش مداوم یک فیدر"""
        reader = ModbusReader(host=device_ip, port=port)
        max_failures = getattr(settings, "MAX_TELEMETRY_FAILURES", 3)
        current_fails = 0

        try:
            while self.is_running:
                try:
                    read_values = {}
                    has_error = False

                    for key, reg_address in registers.items():
                        if reg_address is not None:
                            data = await reader.read_data(address=reg_address, count=1, slave=modbus_address)
                            if data:
                                read_values[key] = data[0]
                            else:
                                has_error = True
                                break
                        else:
                            read_values[key] = 0.0

                    if not has_error and read_values:
                        current_fails = 0
                        await self.handle_success(feeder_id, read_values)
                    else:
                        current_fails += 1
                        await self.handle_failure(feeder_id, current_fails, "Failed to read one or more registers.")

                except asyncio.CancelledError:
                    # توقف تمیز تسک هنگام لغو
                    raise
                except Exception as e:
                    current_fails += 1
                    await self.handle_failure(feeder_id, current_fails, f"Modbus Read Error: {str(e)}")

                if current_fails >= max_failures:
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(polling_interval)
        except asyncio.CancelledError:
            logger.info(f"🛑 Polling task cancelled for Feeder ID {feeder_id}")
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

    async def _sync_feeders_loop(self):
        """حلقه دوره‌ای برای همگام‌سازی فیدرهای فعال (افزودن و حذف خودکار بدون نیاز به ری‌استارت)"""
        default_interval = getattr(settings, "POLLING_INTERVAL", 300)
        sync_interval = getattr(settings, "FEEDER_SYNC_INTERVAL", 1000)  # هر ۱۰ ثانیه چک می‌کند

        while self.is_running:
            try:
                active_feeders = await self.get_active_feeders_from_api()
                current_active_ids = set()

                for feeder in active_feeders:
                    feeder_id = feeder.get("feeder_id") or feeder.get("id")
                    ip = feeder.get("ip_address")
                    port = feeder.get("port", 502)
                    modbus_addr = feeder.get("slave_id") if feeder.get("slave_id") is not None else feeder.get("modbus_address", 1)
                    interval = feeder.get("scan_interval") or default_interval

                    if not (feeder_id and ip):
                        continue

                    current_active_ids.add(feeder_id)

                    registers = {
                        "active_power": feeder.get("active_power_register", 0),
                        "reactive_power": feeder.get("reactive_power_register", 1),
                        "voltage": feeder.get("voltage_register", 2),
                        "current": feeder.get("current_register", 3),
                        "power_factor": feeder.get("power_factor_register", 4)
                    }

                    config_fingerprint = {
                        "ip": ip,
                        "port": port,
                        "modbus_addr": modbus_addr,
                        "interval": interval,
                        "registers": registers
                    }

                    # ۱. بررسی تغییر کانفیگ فیدر موجود
                    if feeder_id in self._tasks:
                        if self._task_configs.get(feeder_id) != config_fingerprint:
                            logger.info(f"🔄 Config changed for Feeder ID {feeder_id}. Restarting task...")
                            self._tasks[feeder_id].cancel()
                            self._tasks.pop(feeder_id, None)

                    # ۲. افزودن فیدر جدید یا تسک بازنشانی‌شده
                    if feeder_id not in self._tasks or self._tasks[feeder_id].done():
                        task = asyncio.create_task(
                            self.poll_device(feeder_id, ip, port, modbus_addr, interval, registers)
                        )
                        self._tasks[feeder_id] = task
                        self._task_configs[feeder_id] = config_fingerprint
                        logger.info(
                            f"➕ Started monitor for Feeder ID {feeder_id} at {ip}:{port} (Modbus Slave ID: {modbus_addr}) every {interval}s."
                        )

                # ۳. حذف فیدرهایی که دیگر فعال نیستند یا حذف شده‌اند
                stale_ids = set(self._tasks.keys()) - current_active_ids
                for stale_id in stale_ids:
                    logger.info(f"➖ Feeder ID {stale_id} is no longer active. Stopping task...")
                    task = self._tasks.pop(stale_id, None)
                    self._task_configs.pop(stale_id, None)
                    if task and not task.done():
                        task.cancel()

            except Exception as e:
                logger.error(f"❌ Error during feeder synchronization: {e}")

            await asyncio.sleep(sync_interval)

    async def start(self):
        """راه‌اندازی ورکر و آغاز حلقه همگام‌سازی"""
        self.is_running = True
        logger.info("🚀 Starting Dynamic Telemetry Scheduler...")
        self._sync_task = asyncio.create_task(self._sync_feeders_loop())

    async def stop(self):
        """توقف کامل و ایمن تمام تسک‌ها"""
        logger.info("🛑 Stopping Telemetry Scheduler...")
        self.is_running = False

        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()

        for task in self._tasks.values():
            if not task.done():
                task.cancel()

        all_tasks = list(self._tasks.values())
        if self._sync_task:
            all_tasks.append(self._sync_task)

        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)

        self._tasks.clear()
        self._task_configs.clear()
        logger.info("All telemetry tasks cleanly stopped.")
