from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ایمپورت روتر و زمان‌بند ماژول تله‌متری
from modules.telemetry.router import router as telemetry_router
from modules.telemetry.scheduler import TelemetryScheduler

logger = logging.getLogger(__name__)

# ساخت یک نمونه از کلاس زمان‌بند
scheduler = TelemetryScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Telemetry Service & Polling Scheduler...")

    # شروع زمان‌بند پایش و خواندن داده‌های Modbus
    try:
        await scheduler.start()
    except Exception as e:
        logger.error(f"❌ Failed to start Telemetry Scheduler: {e}", exc_info=True)

    yield  # سرور در حال کار و آماده پاسخگویی به درخواست‌های REST و Worker

    logger.info("🛑 Shutting down Telemetry Service...")
    # توقف ایمن تمامی تسک‌های Modbus، کلاینت‌ها و ارتباطات
    try:
        await scheduler.stop()
    except Exception as e:
        logger.error(f"❌ Error during scheduler shutdown: {e}", exc_info=True)


app = FastAPI(
    title="Telemetry Microservice",
    description="High-Performance Modbus Polling, InfluxDB Storage & Redis Publisher",
    version="1.0.0",
    lifespan=lifespan
)

# تنظیمات CORS در صورت نیاز به فراخوانی مستقیم
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ثبت روتر تله‌متری
app.include_router(telemetry_router)