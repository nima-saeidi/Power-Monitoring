from fastapi import FastAPI
import asyncio

# ایمپورت کلاس جدید زمان‌بند
from telemetry_service.scheduler import TelemetryScheduler

# اگر در فایل router.py روت‌هایی تعریف کرده‌اید (مانند تصویر پوشه‌هایتان)
# می‌توانید آن را در اینجا ایمپورت کنید:
from modules.telemetry.router import router as telemetry_router

app = FastAPI(title="Telemetry Service", description="Modbus Reading and Redis Publishing")

# ساخت یک نمونه از کلاس زمان‌بند
scheduler = TelemetryScheduler()

@app.on_event("startup")
async def startup_event():
    print("Starting Telemetry Service...")
    # اجرای زمان‌بند به صورت غیرهمگام (خود این متد تسک‌ها را در بک‌گراند می‌سازد)
    await scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down Telemetry Service...")
    # توقف ایمن تمامی تسک‌های متصل به Modbus و Redis
    await scheduler.stop()

# اگر روتر دارید، آن را اضافه کنید (اختیاری)
app.include_router(telemetry_router, prefix="/api/telemetry", tags=["Telemetry"])
