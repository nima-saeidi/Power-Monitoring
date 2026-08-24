from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Power Monitoring System"

    DATABASE_URL: str
    REDIS_URL: str

    SECRET_KEY: str = "dfpgoudrgjfdjgr9ugagkpsdlgkspt94"
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    POLLING_INTERVAL: int = 5000

    MAX_TELEMETRY_FAILURES: int = 3

    critical_threshold: float = 0.7
    warning_threshold: float = 0.4

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
