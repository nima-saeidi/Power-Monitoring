import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, computed_field

class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_NOTIFICATION_QUEUE: str = "notification_events"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    SMTP_HOST: str = Field("smtp.gmail.com", validation_alias=AliasChoices("SMTP_HOST", "SMTP_SERVER"))
    SMTP_PORT: int = 587
    SMTP_USER: str = Field("", validation_alias=AliasChoices("SMTP_USER", "SMTP_USERNAME"))
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    SMS_API_URL: str = "https://api.sms-provider.com/v1/send"
    SMS_API_KEY: str = ""
    SMS_LINE_NUMBER: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s : %(message)s"
)
