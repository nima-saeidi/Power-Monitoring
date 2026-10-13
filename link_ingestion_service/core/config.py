from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    TELEMETRY_EXCHANGE: str = "telemetry_events"

    MAIN_API_URL: str = "http://api:8000"
    INTERNAL_API_KEY: str = ""

    # How often the list of links (and their source config) is re-read from main_api.
    LINK_SOURCE_SYNC_INTERVAL: int = 30
    # Poll interval for a link whose external_source has no `interval`.
    LINK_POLL_INTERVAL: int = 60
    # Consecutive failures before a `link.alert.source_offline` event is published.
    LINK_MAX_FAILURES: int = 3
    # Back-off interval while a link source is offline.
    LINK_OFFLINE_RETRY_INTERVAL: int = 300

    # Generic HTTP provider (provider = "http"). The URL template gets {external_id}.
    LINK_API_URL_TEMPLATE: str = ""
    LINK_API_TOKEN: str = ""
    LINK_API_AUTH_HEADER: str = "Authorization"
    LINK_API_AUTH_SCHEME: str = "Bearer"
    LINK_API_TIMEOUT: float = 10.0
    LINK_API_VERIFY_SSL: bool = True

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
