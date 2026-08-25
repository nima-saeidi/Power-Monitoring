# main_api/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # --- تنظیمات زیرساختی و ثابت (از فایل .env خوانده می‌شوند) ---
    PROJECT_NAME: str = "Power Monitoring System"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str = "dfpgoudrgjfdjgr9ugagkpsdlgkspt94"
    ALGORITHM: str = "HS256"

    # نکته:
    # تنظیمات زیر از این فایل حذف شدند چون اکنون از طریق دیتابیس و ماژول settings
    # به‌صورت داینامیک مدیریت می‌شوند:
    # - ACCESS_TOKEN_EXPIRE_MINUTES
    # - POLLING_INTERVAL
    # - MAX_TELEMETRY_FAILURES
    # - critical_threshold
    # - warning_threshold

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
