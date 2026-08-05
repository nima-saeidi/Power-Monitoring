from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Power Monitoring System"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@localhost:5432/power_monitoring"
    
    # تنظیمات امنیتی و توکن
    SECRET_KEY: str = "dfpgoudrgjfdjgr9ugagkpsdlgkspt94r"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # اعتبار توکن: ۱ روز


    POLLING_INTERVAL: int = 5  # زمان نمونه‌برداری به ثانیه
    MAX_TELEMETRY_FAILURES: int = 3 

    class Config:
        env_file = ".env"

settings = Settings()
