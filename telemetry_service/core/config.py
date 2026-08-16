from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # تنظیمات دیتابیس (مشترک با سرویس اصلی اما با کانکشن پول اختصاصی)
    DATABASE_URL: str

    # تنظیمات Redis برای Pub/Sub
    REDIS_URL: str = "redis://localhost:6379/0"

    # در صورت نیاز به ارتباط HTTP بین سرویس اصلی و تله‌متری (اختیاری)
    INTERNAL_API_KEY: str = "super_secret_internal_key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
