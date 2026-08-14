import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ایمپورت‌های مربوط به دیتابیس
from main_api.core.database import engine, Base

# ایمپورت روترهای ماژول Auth
from main_api.modules.auth.auth_router import auth_router
from main_api.modules.auth.user_router import user_router

# ایمپورت روترهای تفکیک‌شده ماژول Devices
from main_api.modules.devices.router import (
    locations_router,
    posts_router,
    feeders_router,
    links_router
)

# ایمپورت روترهای سایر ماژول‌ها (در صورت وجود)
from main_api.modules.settings.router import router as settings_router
from main_api.modules.notifications.router import router as notifications_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # هنگام بالا آمدن سرور: ساخت جداول در دیتابیس (در صورت عدم وجود)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="سامانه مدیریت و مانیتورینگ شبکه توزیع برق دانشگاه",
    version="1.1.0",
    lifespan=lifespan
)

# تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ثبت روترهای Auth
app.include_router(auth_router)
app.include_router(user_router)

# ثبت روترهای Devices
app.include_router(locations_router)
app.include_router(posts_router)
app.include_router(feeders_router)
app.include_router(links_router)

# ثبت روترهای سایر ماژول‌ها
app.include_router(notifications_router)
app.include_router(settings_router)


if __name__ == "__main__":
    # اجرای اپلیکیشن
    uvicorn.run("main_api.main:app", host="0.0.0.0", port=8000, reload=True)
