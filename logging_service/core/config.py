from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "logging_service"
    PORT: int = 8003

    # تنظیمات Graylog REST API
    GRAYLOG_API_URL: str = "http://graylog:9000/api"
    GRAYLOG_USERNAME: str = "admin"
    GRAYLOG_PASSWORD: str = "admin"

    # اختیاری: توکن اعتبارسنجی بین سرویسی
    INTERNAL_API_KEY: str = "secret-internal-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
