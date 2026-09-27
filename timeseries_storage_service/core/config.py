import os
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    TELEMETRY_EXCHANGE: str = "telemetry_events"
    TIMESERIES_QUEUE: str = "telemetry_timeseries_queue"
    ROUTING_KEY: str = "telemetry.*"

    INFLUXDB_URL: str = Field("http://influxdb:8086", validation_alias=AliasChoices("INFLUXDB_URL", "INFLUX_URL"))
    INFLUXDB_TOKEN: str = Field("my-super-secret-auth-token", validation_alias=AliasChoices("INFLUXDB_TOKEN", "INFLUX_TOKEN"))
    INFLUXDB_ORG: str = Field("power_monitoring_org", validation_alias=AliasChoices("INFLUXDB_ORG", "INFLUX_ORG"))
    INFLUXDB_BUCKET: str = Field("power_monitoring_telemetry", validation_alias=AliasChoices("INFLUXDB_BUCKET", "INFLUX_BUCKET"))

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
