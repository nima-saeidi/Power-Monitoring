import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.consumer import start_consumer
from modules.routers import router as logs_router

# ایمپورت engine و Base و مدل‌ها برای رجیستر شدن جدول‌ها در PostgreSQL
from core.database import engine, Base
import modules.models  # حتماً ایمپورت شود تا مدل‌ها در Base شناسایی شوند

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ۱. ساخت خودکار جداول در صورت عدم وجود (Database Initialization)
    # این بخش جداول مربوط به لاگ را در دیتابیس PostgreSQL می‌سازد
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
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
