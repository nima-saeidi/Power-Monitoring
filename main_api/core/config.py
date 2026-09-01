from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Power Monitoring System"
    DATABASE_URL: str
    SECRET_KEY: str = "dfpgoudrgjfdjgr9ugagkpsdlgkspt94"
    ALGORITHM: str = "HS256"
    TELEMETRY_SERVICE_URL: str = ""
    # تنظیمات جدید برای ایمیل
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""  # در فایل .env پر شود
    SMTP_PASSWORD: str = ""  # در فایل .env پر شود
    FRONTEND_URL: str = "http://localhost:3000"  # آدرس فرانت‌اند برای لینک بازیابی

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
