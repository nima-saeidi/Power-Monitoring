from sqlalchemy import Column, Integer, Float
from core.database import  Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # ضرایب محاسباتی
    alfa = Column(Float, default=0.7, nullable=False)
    beta = Column(Float, default=0.4, nullable=False)

    # تنظیمات امنیتی و نشست‌ها
    access_token_expire_minutes = Column(Integer, default=1440, nullable=False)  # 24 * 60 (۱ روز)

    # تنظیمات جمع‌آوری داده و تله‌متری (Modbus Polling)
    polling_interval = Column(Integer, default=5, nullable=False)  # ثانیه
    max_telemetry_failures = Column(Integer, default=3, nullable=False)  # حداکثر تلاش/خطای مجاز
