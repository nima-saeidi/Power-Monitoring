import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.database import engine, Base
from modules.auth.router import router as auth_router
from modules.devices.router import router as devices_router
from modules.settings.router import router as settings_router  # اضافه شدن روتر تنظیمات
from scheduler import TelemetryScheduler

scheduler = TelemetryScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # هنگام بالا آمدن سرور: ساخت جداول در دیتابیس (در صورت عدم وجود)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # هنگام بالا آمدن سرور: اجرای تسک‌های پس‌زمینه خواندن Modbus
    print("Starting Modbus Telemetry Tasks...")
    task = asyncio.create_task(scheduler.start())

    yield

    # هنگام خاموش شدن سرور: متوقف کردن تسک‌ها
    print("Stopping Telemetry Tasks...")
    await scheduler.stop()
    task.cancel()  # پایان دادن تمیز به تسک


app = FastAPI(
    title="سامانه مدیریت و مانیتورینگ شبکه توزیع برق دانشگاه",
    version="1.1.0",
    lifespan=lifespan
)

# رجیستر کردن روترها
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(settings_router)  # رجیستر کردن روتر تنظیمات داینامیک

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
