import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from core.database import engine, Base
from modules.auth.router import router as auth_router
from modules.devices.router import router as devices_router
from modules.settings.router import router as settings_router  # اضافه شدن روتر تنظیمات
from scheduler import TelemetryScheduler
from modules.notifications.router import router as notifications_router
from modules.auth.models import User
from modules.devices.models import Post, Feeder

from fastapi import FastAPI



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
    task.cancel() 


app = FastAPI(
    title="سامانه مدیریت و مانیتورینگ شبکه توزیع برق دانشگاه",
    version="1.1.0",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(notifications_router)
app.include_router(notifications_router)
app.include_router(settings_router)  

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
