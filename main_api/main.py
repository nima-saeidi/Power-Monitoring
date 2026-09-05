import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
from main_api.core.broker import message_broker, send_log_to_rabbitmq

# ماژول‌های برنامه و روترها
from main_api.modules.auth.auth_router import auth_router
from main_api.modules.auth.user_router import user_router
from main_api.modules.devices.router import (
    locations_router,
    posts_router,
    feeders_router,
    links_router,
)
from main_api.modules.settings.router import router as settings_router
from main_api.modules.notifications.router import router as notifications_router
from main_api.modules.telemetry.router import router as telemetry_router

# پیکربندی اولیه لاگر
setup_logging(service_name="main_api")
logger = logging.getLogger("main_api")


# =======================================================
# مدیریت چرخه حیات برنامه (Lifespan Events)
# =======================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- Startup --------
    logger.info("🚀 Main API is starting up...")

    # اتصال به RabbitMQ جهت ارسال لاگ‌ها و انتشار رویدادهای مانیتورینگ
    try:
        await message_broker.connect()
        logger.info("✅ Connected to RabbitMQ message broker successfully.")

        # لاگ سیستمی آغاز به کار
        await send_log_to_rabbitmq(
            level="INFO",
            message="Main API service started successfully.",
            service="main_api",
            extra_data={"status": "online"}
        )
    except Exception as e:
        logger.error(f"❌ Failed to connect to RabbitMQ broker: {e}", exc_info=True)

    yield  # برنامه در حال سرویس‌دهی است

    # -------- Shutdown --------
    logger.info("🛑 Main API is shutting down...")

    # بستن ایمن ارتباط با RabbitMQ
    try:
        await send_log_to_rabbitmq(
            level="INFO",
            message="Main API service is shutting down.",
            service="main_api",
            extra_data={"status": "offline"}
        )
        await message_broker.close()
        logger.info("✅ RabbitMQ connection closed cleanly.")
    except Exception as e:
        logger.error(f"❌ Error while closing RabbitMQ connection: {e}", exc_info=True)


# =======================================================
# نمونه‌سازی FastAPI و میدلورها
# =======================================================
app = FastAPI(
    title="سامانه جامع مانیتورینگ و مدیریت شبکه توزیع برق دانشگاه",
    description="سرویس مرکزی API برای مدیریت تجهیزات، کاربران و انتشار رویدادهای مانیتورینگ به RabbitMQ",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
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

# ۰. مدیریت خطای Rate Limit (کد 429)
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for IP: {request.client.host if request.client else 'unknown'}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "message": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کرده و مجدداً تلاش کنید.",
            "error_code": "RATE_LIMIT_EXCEEDED"
        },
    )


# ۱. مدیریت خطاهای اعتبارسنجی Pydantic (کد 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    persian_errors = []

    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        msg = error.get("msg", "")

        # ترجمه و شفاف‌سازی خطاهای رایج Pydantic
        if "Field required" in msg:
            persian_msg = "ارسال این فیلد الزامی است."
        elif "value is not a valid integer" in msg:
            persian_msg = "مقدار باید عدد صحیح باشد."
        elif "value is not a valid float" in msg:
            persian_msg = "مقدار باید عدد اعشاری باشد."
        elif "String should have at least" in msg:
            persian_msg = "طول متن کمتر از حد مجاز است."
        elif "value is not a valid boolean" in msg:
            persian_msg = "مقدار باید بولین (True/False) باشد."
        else:
            persian_msg = msg

        persian_errors.append({"field": field, "message": persian_msg})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "اطلاعات ارسالی نامعتبر است.",
            "error_code": "VALIDATION_ERROR",
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
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}"
        },
    )


# ۳. مدیریت خطاهای یکپارچگی پایگاه داده (IntegrityError)
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    orig_error = str(exc.orig) if hasattr(exc, "orig") else str(exc)
    logger.error(f"Database IntegrityError: {orig_error}")

    await send_log_to_rabbitmq(
        level="ERROR",
        message=f"Database Integrity Error: {orig_error}",
        service="main_api",
        extra_data={"path": request.url.path}
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "خطا در پایگاه داده: ممکن است داده ارسالی تکراری باشد یا اطلاعات وابسته (مانند کلید خارجی) نامعتبر باشد.",
            "error_code": "DB_INTEGRITY_ERROR"
        }
    )


# ۴. مدیریت سایر خطاهای دیتابیس (SQLAlchemyError)
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_general_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "خطای سیستمی در ارتباط با پایگاه داده رخ داده است.",
            "error_code": "DATABASE_ERROR"
        }
    )


# ۵. مدیریت خطاهای پیش‌بینی‌نشده سیستمی (Unhandled 500)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)

    await send_log_to_rabbitmq(
        level="CRITICAL",
        message=f"Unhandled 500 Exception: {str(exc)}",
        service="main_api",
        extra_data={"path": request.url.path, "method": request.method}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "یک خطای داخلی در سرور رخ داده است. لطفاً با پشتیبانی تماس بگیرید.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


# =======================================================
# روت‌های سیستمی، سلامت و تست
# =======================================================

@app.get("/health", tags=["System / Monitoring"], summary="بررسی سلامت سرویس")
async def health_check():
    """بررسی وضعیت کارکرد Main API و اتصال به RabbitMQ"""
    broker_connected = message_broker.is_connected if hasattr(message_broker, "is_connected") else True
    return {
        "status": "healthy" if broker_connected else "degraded",
        "service": "main_api",
        "rabbitmq_connected": broker_connected
    }


@app.post("/test-log", tags=["System / Testing"], summary="ارسال لاگ تستی")
async def create_test_log(message: str = "Test log event", level: str = "INFO"):
    """ارسال دستی لاگ تستی به صف RabbitMQ جهت بررسی کارکرد سرویس لاگینگ"""
    await send_log_to_rabbitmq(
        level=level,
        message=message,
        service="main_api",
        extra_data={"action": "manual_test"}
    )
    return {"status": "success", "message": "Log sent to queue"}


# =======================================================
# ثبت روترها (Include Routers)
# =======================================================

# احراز هویت و مدیریت کاربران
app.include_router(auth_router)
app.include_router(user_router)

# تجهیزات و ساختار شبکه توزیع
app.include_router(locations_router)
app.include_router(posts_router)
app.include_router(feeders_router)
app.include_router(links_router)

# تله‌متری و داده‌های مانیتورینگ
app.include_router(telemetry_router)

# نوتیفیکیشن‌ها و تنظیمات سامانه
app.include_router(notifications_router)
app.include_router(settings_router)

if __name__ == "__main__":
    uvicorn.run("main_api.main:app", host="0.0.0.0", port=8000, reload=True)
