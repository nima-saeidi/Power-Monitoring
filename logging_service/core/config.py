# logging_service/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "logging_service"
    PORT: int = 8002

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@db:5432/power_logs"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    # Graylog GELF (UDP) Specs - برای ارسال لاگ از Consumer
    GRAYLOG_HOST: str = "graylog"
    GRAYLOG_PORT: int = 12201

    # Graylog REST API Specs - برای خواندن لاگ‌ها (در صورت نیاز)
    GRAYLOG_API_URL: str = "http://graylog:9000/api"
    GRAYLOG_USERNAME: str = "admin"
    GRAYLOG_PASSWORD: str = "admin"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
