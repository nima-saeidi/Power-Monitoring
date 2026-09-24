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
    FRONTEND_URL: str = "http://localhost:3000"  # آدرس فرانت‌اند برای لینک بازیابی
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    LOGGING_SERVICE_URL: str = "http://logging:8002/api/v1"
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
