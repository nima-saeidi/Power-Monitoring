from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    TELEMETRY_EXCHANGE: str = "telemetry_events"

    MAIN_API_URL: str = "http://api:8000"
    INTERNAL_API_KEY: str = ""

    INFLUXDB_URL: str = Field("http://influxdb:8086", validation_alias=AliasChoices("INFLUXDB_URL", "INFLUX_URL"))
    INFLUXDB_TOKEN: str = Field("", validation_alias=AliasChoices("INFLUXDB_TOKEN", "INFLUX_TOKEN"))
    INFLUXDB_ORG: str = Field("", validation_alias=AliasChoices("INFLUXDB_ORG", "INFLUX_ORG"))
    INFLUXDB_BUCKET: str = Field("", validation_alias=AliasChoices("INFLUXDB_BUCKET", "INFLUX_BUCKET"))

    # Seconds between live readings (same cadence as the real Modbus poller).
    FAKE_INTERVAL: float = 5.0
    # How often the feeder list is re-read from main_api.
    FAKE_SYNC_INTERVAL: int = 60
    # Comma separated feeder ids to restrict to; empty = every active feeder.
    FAKE_FEEDER_IDS: str = ""
    # Only fake feeders the poller reports as offline, so real readings are never mixed with demo data.
    FAKE_ONLY_OFFLINE: bool = True
    # History written straight to InfluxDB on start-up for feeders that have a gap.
    FAKE_BACKFILL_DAYS: int = 30
    FAKE_BACKFILL_STEP_SECONDS: int = 60
    # Upper bound of current / rated current. Keep it below the warning threshold
    # (system settings), otherwise demo data raises real load alerts.
    FAKE_MAX_LOAD_RATIO: float = 0.35

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @property
    def feeder_filter(self) -> Optional[set]:
        ids = {int(x) for x in self.FAKE_FEEDER_IDS.split(",") if x.strip()}
        return ids or None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
