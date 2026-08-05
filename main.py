from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.database import engine, Base
from modules.auth.router import router as auth_router
from modules.devices.router import router as devices_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ساخت جداول دیتابیس در هنگام استارت
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="سامانه مدیریت و مانیتورینگ شبکه توزیع برق دانشگاه",
    version="1.1.0",
    lifespan=lifespan
)

# رجیستر کردن روترها
app.include_router(auth_router)
app.include_router(devices_router)

