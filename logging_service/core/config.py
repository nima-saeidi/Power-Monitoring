import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)

# Ship every logger's records to Graylog (root logger, not just this one) -
# ops has no server access, only the Graylog port. Note: this is separate
# from GraylogClient (which *reads* Graylog's search API) - this is what
# actually gets this service's own logs *into* Graylog in the first place.
# Never fatal on failure.
try:
    import graypy
    _gelf_handler = graypy.GELFUDPHandler(
        settings.GRAYLOG_HOST,
        settings.GRAYLOG_PORT,
        debugging_fields=True,
        extra_fields=True,
    )
    _gelf_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(_gelf_handler)
except Exception as _graylog_err:
    logging.getLogger(__name__).warning(f"Could not attach Graylog handler: {_graylog_err}")
