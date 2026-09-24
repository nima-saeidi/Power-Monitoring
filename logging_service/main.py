import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core.config import settings
from core.consumer import start_consumer
from modules.routers import router as logs_router

# ایمپورت engine و Base و مدل‌ها برای رجیستر شدن جدول‌ها در PostgreSQL
from core.database import engine, Base
import modules.models  # حتماً ایمپورت شود تا مدل‌ها در Base شناسایی شوند

logger = logging.getLogger(__name__)


# ایندکس‌های تکمیلی که برای بهینه‌سازی گزارش‌گیری روی جدولی با میلیون‌ها رکورد لازم‌اند
# و چون این سرویس Alembic ندارد (فقط create_all)، این ایندکس‌ها را با IF NOT EXISTS
# به‌صورت idempotent در استارت‌آپ می‌سازیم تا هم روی دیتابیس‌های تازه و هم قدیمی اعمال شوند.
_EXTRA_INDEX_STATEMENTS = [
    # فعال‌سازی pg_trgm برای جستجوی سریع ILIKE ('%...%') روی action/service_name
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_action_trgm ON service_logs USING gin (action gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_service_name_trgm ON service_logs USING gin (service_name gin_trgm_ops)",
    # فیلترهای severity/success داخل details (JSONB) بدون ایندکس، اسکن کامل جدول انجام می‌دادند
    "CREATE INDEX IF NOT EXISTS ix_service_logs_severity ON service_logs ((details->>'severity'))",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_success ON service_logs ((details->>'success'))",
    # ایندکس‌های ترکیبی برای الگوی رایج «فیلتر روی یک ستون + مرتب‌سازی بر اساس created_at»
    "CREATE INDEX IF NOT EXISTS ix_service_logs_service_created ON service_logs (service_name, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_action_created ON service_logs (action, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_user_created ON service_logs (user_id, created_at DESC)",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ۱. ساخت خودکار جداول در صورت عدم وجود (Database Initialization)
    # این بخش جداول مربوط به لاگ را در دیتابیس PostgreSQL می‌سازد
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            logger.info("Ensuring reporting indexes exist on service_logs...")
            for statement in _EXTRA_INDEX_STATEMENTS:
                try:
                    await conn.execute(text(statement))
                except Exception as idx_err:
                    # عدم موفقیت در ساخت یک ایندکس (مثلاً کمبود دسترسی برای CREATE EXTENSION)
                    # نباید کل استارت‌آپ سرویس را متوقف کند.
                    logger.warning(f"Could not ensure index ({statement[:60]}...): {idx_err}")

        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    # ۲. شروع Consumer به عنوان تسک پس‌زمینه در زمان استارت‌آپ
    # این تسک پیام‌ها را از RabbitMQ می‌خواند و در PostgreSQL و Graylog ذخیره می‌کند
    logger.info("Starting RabbitMQ Consumer task...")
    consumer_task = asyncio.create_task(start_consumer())

    yield

    # ۳. توقف و کنسل کردن تسک هنگام خاموش شدن سرویس (Graceful Shutdown)
    logger.info("Stopping RabbitMQ Consumer task...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("RabbitMQ Consumer task cancelled successfully.")


app = FastAPI(
    title="Power Monitoring - Logging & Audit Service",
    description="Service to consume audit logs from RabbitMQ and store them in PostgreSQL & Graylog",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# اضافه کردن روت‌های ماژول (مثل GET /logs برای خواندن از دیتابیس)
app.include_router(logs_router, prefix="/api/v1")


# ۴. اندپوینت بررسی سلامت سرویس (برای داکر و مانیتورینگ)
@app.get("/", tags=["Health Check"])
async def health_check():
    return {
        "service": "Logging & Audit Service",
        "status": "running",
        "rabbitmq_consumer": "active background task",
        "storage_destinations": ["PostgreSQL", "Graylog GELF UDP"]
    }


if __name__ == "__main__":
    import uvicorn
    # دریافت پورت از تنظیمات، با پیش‌فرض امن ۸۰۰۰
    port = getattr(settings, "PORT", 8000)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
