import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # تنظیمات RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_QUEUE: str = "telemetry_events"

    # تنظیمات InfluxDB
    INFLUXDB_URL: str = "http://db:8086"
    INFLUXDB_TOKEN: str = "my-super-secret-auth-token"
    INFLUXDB_ORG: str = "power_monitoring_org"
    INFLUXDB_BUCKET: str = "power_monitoring_telemetry"

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
