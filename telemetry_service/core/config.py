from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # تنظیمات دیتابیس رابطه‌ای (TimescaleDB / Postgres)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@localhost:5432/power_monitoring"

    # تنظیمات ردیس
    CACHE_URL: str = "redis://127.0.0.1:6379/0"

    INFLUX_URL: str = "http://influxdb:8086"
    INFLUX_TOKEN: str = "super-secret-token-for-power"
    INFLUX_ORG: str = "power_org"
    INFLUX_BUCKET: str = "telemetry_bucket"

    # تنظیمات سرویس تلمتری
    POLLING_INTERVAL: int = 5
    MAX_TELEMETRY_FAILURES: int = 3

    # کلید امنیتی و آدرس API اصلی
    INTERNAL_API_KEY: str = "super_secret_internal_key"
    MAIN_API_URL: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # نادیده گرفتن متغیرهای اضافی در env
    )


settings = Settings()
