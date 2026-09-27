from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "logging_service"
    PORT: int = 8002

    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@db:5432/power_logs"

    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    GRAYLOG_HOST: str = "graylog"
    GRAYLOG_PORT: int = 12201

    GRAYLOG_API_URL: str = "http://graylog:9000/api"
    GRAYLOG_USERNAME: str = "admin"
    GRAYLOG_PASSWORD: str = "admin"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
