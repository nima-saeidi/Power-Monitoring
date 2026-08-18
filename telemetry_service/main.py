from fastapi import FastAPI
import asyncio

# --- ۱. ایمپورت‌های مربوط به دیتابیس (مسیر را در صورت نیاز اصلاح کنید) ---
from core.database import engine, Base
# -----------------------------------------------------------------------

# ایمپورت کلاس جدید زمان‌بند
from scheduler import TelemetryScheduler

# ایمپورت روتر
from modules.telemetry.router import router as telemetry_router

app = FastAPI(title="Telemetry Service", description="Modbus Reading and Redis Publishing")

# ساخت یک نمونه از کلاس زمان‌بند
scheduler = TelemetryScheduler()


# --- ۲. تابع ساخت جداول به صورت Async برای جلوگیری از خطای MissingGreenlet ---
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    print("Starting Telemetry Service...")

    # --- ۳. فراخوانی ساخت جداول قبل از اجرای زمان‌بند ---
    await init_models()
    # --------------------------------------------------

    # اجرای زمان‌بند به صورت غیرهمگام
    await scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Telemetry Service...")
    # توقف ایمن تمامی تسک‌های متصل به Modbus و Redis
    await scheduler.stop()


# اضافه کردن روتر
app.include_router(telemetry_router, prefix="/api/telemetry", tags=["Telemetry"])
