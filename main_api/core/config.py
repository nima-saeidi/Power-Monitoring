from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Power Monitoring System"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:n1m010@localhost:5432/power_monitoring"
    SECRET_KEY: str = "dfpgoudrgjfdjgr9ugagkpsdlgkspt94r"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    POLLING_INTERVAL: int = 5000
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    MAX_TELEMETRY_FAILURES: int = 3
    critical_threshold: float = 0.7
    warning_threshold: float = 0.4
    CACHE_URL: str = "redis://127.0.0.1:6379/0"

    # استفاده از روش Pydantic V2 برای تنظیمات
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
