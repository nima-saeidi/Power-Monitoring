from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    # RabbitMQ Settings
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_NOTIFICATION_QUEUE: str = "notification_events"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    # SMTP Settings (Email)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@powermonitoring.com"
    SMTP_USE_TLS: bool = True

    # SMS Settings (مثلاً کاوه‌نگار، فراز اس‌ام‌اس یا هر پنل دلخواه)
    SMS_API_KEY: str = ""
    SMS_LINE_NUMBER: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
