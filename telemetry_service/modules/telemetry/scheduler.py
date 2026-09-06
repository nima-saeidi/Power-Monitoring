import asyncio
import json
import logging
from datetime import datetime, timezone
import httpx
import aio_pika

# ایمپورت تنظیمات و ماژول‌ها
from core.config import settings
from modules.telemetry.modbus_client import ModbusReader

# تنظیمات لاگر
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("telemetry_scheduler")


class TelemetryScheduler:
    def __init__(self):
        self.is_running = False
        # نگهداری تسک‌ها و تنظیمات بر اساس feeder_id
        self._tasks: dict[int, asyncio.Task] = {}
        self._task_configs: dict[int, dict] = {}
        self._sync_task: asyncio.Task | None = None

        # مدیریت اتصال پایدار RabbitMQ
        self._rmq_connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._rmq_channel: aio_pika.abc.AbstractChannel | None = None
        self._telemetry_exchange: aio_pika.abc.AbstractExchange | None = None

    async def _init_rabbitmq(self):
        """راه‌اندازی اتصال و Exchange در RabbitMQ"""
        try:
            rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
            exchange_name = getattr(settings, "TELEMETRY_EXCHANGE", "telemetry_events")

            self._rmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            self._rmq_channel = await self._rmq_connection.channel()

            self._telemetry_exchange = await self._rmq_channel.declare_exchange(
                name=exchange_name,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info(f"✅ RabbitMQ publisher connected. Exchange: '{exchange_name}'")
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}", exc_info=True)
            raise

    async def _publish_event(self, routing_key: str, payload: dict):
        """ارسال امن پیام به Exchange در RabbitMQ"""
        if not self._telemetry_exchange:
            logger.error("RabbitMQ exchange is not ready. Message dropped.")
            return

        try:
            message_body = json.dumps(payload, default=str).encode("utf-8")
            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await self._telemetry_exchange.publish(message, routing_key=routing_key)
        except Exception as e:
            logger.error(f"❌ Error publishing event to {routing_key}: {e}")

    async def handle_success(self, feeder_id: int, values: dict):
        """پردازش ۵ پارامتر الکتریکی و ارسال پیام Event به RabbitMQ برای ذخیره‌سازی سری‌زمانی"""
        active_power_val = float(values.get('active_power', 0.0))
        reactive_power_val = float(values.get('reactive_power', 0.0))
        voltage_val = float(values.get('voltage', 0.0))
        current_val = float(values.get('current', 0.0))
        power_factor_val = float(values.get('power_factor', 0.0))
        now_utc = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"📊 Feeder {feeder_id} Data | "
            f"Active: {active_power_val:.2f} W | "
            f"Reactive: {reactive_power_val:.2f} VAr | "
            f"V: {voltage_val:.2f} V | "
            f"I: {current_val:.2f} A | "
            f"PF: {power_factor_val:.2f}"
        )

        payload = {
            "feeder_id": feeder_id,
            "active_power": active_power_val,
            "reactive_power": reactive_power_val,
            "voltage": voltage_val,
            "current": current_val,
            "power_factor": power_factor_val,
            "timestamp": now_utc
        }

        # انتشار داده برای مصرف در timeseries_storage_service
        await self._publish_event(routing_key="telemetry.metric", payload=payload)

    async def handle_failure(self, feeder_id: int, current_failures: int, error_msg: str):
        """ارسال رویداد خطا/هشدار در صورت عدم پاسخگویی تجهیز به صف رخدادها"""
        logger.warning(
            f"⚠️ Feeder ID {feeder_id} failed to respond. Failures: {current_failures} | Error: {error_msg}"
        )

        # انتشار لاگ یا آلرت تجهیز برای سیستم مانیتورینگ/لاگینگ
        alert_payload = {
            "feeder_id": feeder_id,
            "failures_count": current_failures,
            "error_message": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self._publish_event(routing_key="telemetry.alert.device_offline", payload=alert_payload)

    async def poll_device(
            self, feeder_id: int, device_ip: str, port: int, modbus_address: int, polling_interval: int, registers: dict
    ):
        """پایش مداوم و ناهمگام یک فیدر با هندل کردن کامل خطاها"""
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
                    raise
                except Exception as e:
                    current_fails += 1
                    await self.handle_failure(feeder_id, current_fails, f"Modbus Read Error: {str(e)}")

                # در صورت خطای متوالی، فاصله زمانی جهت جلوگیری از Spam افزایش می‌یابد
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
        main_api_url = getattr(settings, "MAIN_API_URL", "http://main_api:8000").rstrip("/")
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
        """حلقه همگام‌سازی دوره‌ای فیدرهای فعال بدون نیاز به ری‌استارت سرویس"""
        default_interval = getattr(settings, "POLLING_INTERVAL", 300)
        sync_interval = getattr(settings, "FEEDER_SYNC_INTERVAL", 10)  # بررسی هر ۱۰ ثانیه

        while self.is_running:
            try:
                active_feeders = await self.get_active_feeders_from_api()
                current_active_ids = set()

                for feeder in active_feeders:
                    feeder_id = feeder.get("feeder_id") or feeder.get("id")
                    ip = feeder.get("ip_address")
                    port = feeder.get("port", 502)
                    modbus_addr = (
                        feeder.get("slave_id")
                        if feeder.get("slave_id") is not None
                        else feeder.get("modbus_address", 1)
                    )
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

                    # ۱. ری‌استارت تسک در صورت تغییر کانفیگ
                    if feeder_id in self._tasks:
                        if self._task_configs.get(feeder_id) != config_fingerprint:
                            logger.info(f"🔄 Config changed for Feeder ID {feeder_id}. Restarting task...")
                            self._tasks[feeder_id].cancel()
                            self._tasks.pop(feeder_id, None)

                    # ۲. شروع تسک جدید یا بازنشانی‌شده
                    if feeder_id not in self._tasks or self._tasks[feeder_id].done():
                        task = asyncio.create_task(
                            self.poll_device(feeder_id, ip, port, modbus_addr, interval, registers)
                        )
                        self._tasks[feeder_id] = task
                        self._task_configs[feeder_id] = config_fingerprint
                        logger.info(
                            f"➕ Started monitor for Feeder ID {feeder_id} at {ip}:{port} "
                            f"(Slave ID: {modbus_addr}) every {interval}s."
                        )

                # ۳. حذف فیدرهای غیرفعال شده
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
        """راه‌اندازی کامل سرویس اسکجولر و اتصال به پیام‌رسان"""
        self.is_running = True
        logger.info("🚀 Starting Dynamic Telemetry Scheduler...")
        await self._init_rabbitmq()
        self._sync_task = asyncio.create_task(self._sync_feeders_loop())

    async def stop(self):
        """توقف ایمن و بستن تسک‌ها و کانکشن‌های باز"""
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

        if self._rmq_connection and not self._rmq_connection.is_closed:
            await self._rmq_connection.close()
            logger.info("RabbitMQ connection closed.")

        logger.info("All telemetry tasks cleanly stopped.")
