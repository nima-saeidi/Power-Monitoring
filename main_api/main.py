import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ایمپورت‌های مربوط به دیتابیس
from main_api.core.database import engine, Base

# ایمپورت روترهای ماژول Auth
from main_api.modules.auth.auth_router import auth_router
from main_api.modules.auth.user_router import user_router
from main_api.modules.telemetry.router import router as telemetry_router
from main_api.modules.reports.router import router as report_router

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

# ================= اضافه شده برای ردیس =================
# فرض بر این است که فایل redis_listener در مسیر زیر قرار دارد.
# اگر مسیر متفاوتی دارید، این ایمپورت را اصلاح کنید.
from main_api.modules.telemetry.redis_listener import listen_to_redis_and_save


# =======================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    # # هنگام بالا آمدن سرور: ساخت جداول در دیتابیس (در صورت عدم وجود)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # ================= اضافه شده برای ردیس =================
    # ایجاد یک تسک پس‌زمینه برای گوش دادن دائمی به ردیس
    redis_task = asyncio.create_task(listen_to_redis_and_save())
    # =======================================================

    yield  # در این نقطه برنامه در حال اجرا و سرویس‌دهی است

    # ================= اضافه شده برای ردیس =================
    # هنگام خاموش شدن سرور: تسک ردیس را متوقف می‌کنیم تا برنامه به‌درستی بسته شود
    redis_task.cancel()
    # =======================================================


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
app.include_router(report_router)

# ثبت روترهای سایر ماژول‌ها
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(telemetry_router)

if __name__ == "__main__":
    # اجرای اپلیکیشن
    uvicorn.run("main_api.main:app", host="0.0.0.0", port=8000, reload=True)
