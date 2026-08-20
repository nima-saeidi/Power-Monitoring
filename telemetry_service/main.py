from contextlib import asynccontextmanager
from fastapi import FastAPI

# ایمپورت کلاس جدید زمان‌بند
from modules.telemetry.scheduler import TelemetryScheduler

# ایمپورت روتر

# ساخت یک نمونه از کلاس زمان‌بند
scheduler = TelemetryScheduler()


# استفاده از lifespan به جای on_event (روش جدید و استاندارد FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Telemetry Service (Pure Worker Mode)...")

    # اجرای زمان‌بند به صورت غیرهمگام (ایجاد تسک‌های خواندن از مودباس)
    await scheduler.start()

    yield  # سرور روشن می‌ماند و درخواست‌ها را پاسخ می‌دهد

    print("🛑 Shutting down Telemetry Service...")
    # توقف ایمن تمامی تسک‌های متصل به Modbus و Redis
    await scheduler.stop()


app = FastAPI(
    title="Telemetry Worker Service",
    description="Pure Modbus Worker & Redis Publisher (No Database Dependencies)",
    lifespan=lifespan
)

