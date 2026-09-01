from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "logging_service"
    PORT: int = 8002

    # Graylog REST API Specs
    GRAYLOG_API_URL: str = "http://graylog:9000/api"
    GRAYLOG_USERNAME: str = "admin"
    GRAYLOG_PASSWORD: str = "admin"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
