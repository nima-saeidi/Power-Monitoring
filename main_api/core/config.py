from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Power Monitoring System"
    DATABASE_URL: str
    # بدون مقدار پیش‌فرض: اگر در .env ست نشده باشد سرویس بالا نمی‌آید (کلید قابل حدس نباشد)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    TELEMETRY_SERVICE_URL: str = ""
    FRONTEND_URL: str = "http://localhost:3000"  # آدرس فرانت‌اند برای لینک بازیابی
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    # Exchange رویدادهای تله‌متری (telemetry_service) برای ارسال زنده به وب‌سوکت
    TELEMETRY_EXCHANGE: str = "telemetry_events"
    LOGGING_SERVICE_URL: str = "http://logging:8002/api/v1"
    # کلید مشترک برای اندپوینت‌های داخلی بین میکروسرویس‌ها (هدر X-Internal-API-Key)
    INTERNAL_API_KEY: str = ""
    # لیست originهای مجاز CORS با کاما جدا شده؛ "*" یعنی همه
    CORS_ORIGINS: str = "*"
    # مستندات Swagger/ReDoc؛ در production خاموش بماند
    ENABLE_DOCS: bool = False
    # محل ذخیره شمارنده‌های rate limit؛ با چند worker یا چند نمونه باید مشترک باشد (مثلاً redis://redis:6379/1)
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
