from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # تغییر نام به CACHE_URL برای فرار از تداخل redis_url
    CACHE_URL: str = "redis://127.0.0.1:6379/0"

    INTERNAL_API_KEY: str = "super_secret_internal_key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # نادیده گرفتن متغیرهای اضافی
    )


settings = Settings()
