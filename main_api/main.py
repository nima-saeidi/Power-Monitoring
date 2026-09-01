import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError

# ================= Rate Limiting =================
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# تعریف محدودکننده (پیش‌فرض: ۱۰۰ درخواست در دقیقه برای هر IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
# =================================================

# هسته لاگینگ و بروکر پیام
from main_api.core.logging import setup_logging
from main_api.core.broker import message_broker

# ماژول‌های برنامه و روترها
from main_api.modules.auth.auth_router import auth_router
from main_api.modules.auth.user_router import user_router
from main_api.modules.devices.router import (
    locations_router,
    posts_router,
    feeders_router,
    links_router
)
from main_api.modules.settings.router import router as settings_router
from main_api.modules.notifications.router import router as notifications_router
from main_api.modules.telemetry.router import router as telemetry_router


# پیکربندی اولیه لاگر
setup_logging(service_name="main_api")
logger = logging.getLogger("main_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- Startup --------
    logger.info("Main API is starting up...")

    # اتصال به RabbitMQ جهت ارسال لاگ‌ها و رویدادها
    try:
        await message_broker.connect()
        logger.info("Connected to RabbitMQ successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ broker: {e}", exc_info=True)

    yield  # برنامه در حال سرویس‌دهی است

    # -------- Shutdown --------
    logger.info("Main API is shutting down...")

    # بستن ایمن ارتباط با RabbitMQ
    try:
        await message_broker.close()
        logger.info("RabbitMQ connection closed cleanly.")
    except Exception as e:
        logger.error(f"Error while closing RabbitMQ connection: {e}")


app = FastAPI(
    title="سامانه مدیریت و مانیتورینگ شبکه توزیع برق دانشگاه",
    version="1.1.0",
    lifespan=lifespan
)

# اتصال Limiter
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================================================
# مدیریت سراسری خطاهای API (Exception Handlers)
# =======================================================

# ۰. مدیریت خطای Rate Limit
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "message": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کرده و مجدداً تلاش کنید."
        },
    )


# ۱. مدیریت خطاهای اعتبارسنجی Pydantic (کد 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    persian_errors = []

    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        msg = error.get("msg", "")

        # ترجمه خطاهای رایج Pydantic
        if "Field required" in msg:
            persian_msg = "ارسال این فیلد الزامی است."
        elif "value is not a valid integer" in msg:
            persian_msg = "مقدار باید عدد صحیح باشد."
        elif "value is not a valid float" in msg:
            persian_msg = "مقدار باید عدد اعشاری باشد."
        elif "String should have at least" in msg:
            persian_msg = "طول متن کمتر از حد مجاز است."
        else:
            persian_msg = msg

        persian_errors.append({"field": field, "message": persian_msg})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "اطلاعات ارسالی نامعتبر است.",
            "details": persian_errors
        },
    )


# ۲. مدیریت خطاهای استاندارد HTTP
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        },
    )


# ۳. مدیریت خطاهای دیتابیس (IntegrityError)
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database IntegrityError: {exc.orig if hasattr(exc, 'orig') else exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "خطا در پایگاه داده: ممکن است داده ارسالی تکراری باشد یا اطلاعات وابسته (مانند شناسه) نامعتبر باشد."
        }
    )


@app.post("/test-log")
async def create_test_log(message: str = "Test log event", level: str = "INFO"):
    await send_log_to_rabbitmq(
        level=level,
        message=message,
        service="main_api",
        extra_data={"user_id": 1, "action": "manual_test"}
    )
    return {"status": "success", "message": "Log sent to queue"}

# =======================================================
# ثبت روترها (Include Routers)
# =======================================================

# احراز هویت و کاربران
app.include_router(auth_router)
app.include_router(user_router)

# تجهیزات و ساختار شبکه
app.include_router(locations_router)
app.include_router(posts_router)
app.include_router(feeders_router)
app.include_router(links_router)

# گزارش‌ها و تله‌متری
app.include_router(telemetry_router)

# نوتیفیکیشن و تنظیمات
app.include_router(notifications_router)
app.include_router(settings_router)




if __name__ == "__main__":
    uvicorn.run("main_api.main:app", host="0.0.0.0", port=8000, reload=True)
