import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError

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
from main_api.modules.telemetry.redis_listener import listen_to_redis_and_save


# =======================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
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


# =======================================================
# مدیریت سراسری خطاهای API (Exception Handlers)
# =======================================================

# ۱. مدیریت خطاهای اعتبارسنجی Pydantic (کد 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    persian_errors = []

    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
        msg = error["msg"]

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


# ۲. مدیریت خطاهای دستی HTTP (کد 400، 404 و ...)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        },
    )


# ۳. مدیریت خطاهای دیتابیس (تکراری بودن داده یا نبودن کلید خارجی)
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "خطا در پایگاه داده: ممکن است داده ارسالی تکراری باشد یا اطلاعات وابسته (مانند شناسه) نامعتبر باشد."
        }
    )


# =======================================================


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
