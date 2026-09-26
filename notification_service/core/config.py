import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, computed_field

class Settings(BaseSettings):
    # Logging Configuration
    LOG_LEVEL: str = "INFO"

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

    # SMTP Settings (Email) — .env مشترک پروژه SMTP_SERVER / SMTP_USERNAME دارد؛ بدون این alias ها
    # نام کاربری خالی خوانده می‌شد و هیچ ایمیلی ارسال نمی‌شد.
    SMTP_HOST: str = Field("smtp.gmail.com", validation_alias=AliasChoices("SMTP_HOST", "SMTP_SERVER"))
    SMTP_PORT: int = 587
    SMTP_USER: str = Field("", validation_alias=AliasChoices("SMTP_USER", "SMTP_USERNAME"))
    SMTP_PASSWORD: str = ""
    # خالی یعنی همان حساب SMTP (Gmail فقط از آدرس خود حساب اجازه‌ی ارسال می‌دهد)
    SMTP_FROM_EMAIL: str = ""
    # STARTTLS روی 587؛ روی 465 اتصال از ابتدا SSL است (خودکار تشخیص داده می‌شود)
    SMTP_USE_TLS: bool = True

    # SMS Settings
    SMS_API_URL: str = "https://api.sms-provider.com/v1/send"
    SMS_API_KEY: str = ""
    SMS_LINE_NUMBER: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# کانفیگ سراسری لاگر
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s : %(message)s"
)
