from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Postgres Storage Worker"
    DATABASE_URL: str
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
