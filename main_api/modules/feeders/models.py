from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base
from sqlalchemy.sql import func


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feeder_id = Column(Integer, index=True, nullable=False)
    key = Column(String, index=True, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True, nullable=False)


class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    # --- اطلاعات پایه فیدر ---
    feeder_type = Column(String(50), nullable=True)  # نوع فیدر: تولید کننده / مصرف کننده
    max_current = Column(Float, nullable=True)  # حداکثر جریان (A)

    # --- تنظیمات ارتباطی شبکه و مدباس ---
    ip_address = Column(String(50), nullable=True)  # آدرس IP فیدر
    port = Column(Integer, nullable=True)  # پورت ارتباطی
    modbus_address = Column(Integer, nullable=True)  # آدرس مدباس (Slave ID / Unit ID)

    # --- رجیسترهای پارامترهای اصلی مدباس ---
    active_power_register = Column(Integer, nullable=True)
    reactive_power_register = Column(Integer, nullable=True)
    voltage_register = Column(Integer, nullable=True)
    current_register = Column(Integer, nullable=True)
    power_factor_register = Column(Integer, nullable=True)

    metadata_info = Column("metadata", JSONB, nullable=True)

    # --- وضعیت و مانیتورینگ ---
    # is_active: کلید دستی ادمین برای فعال/غیرفعال کردن پایش این فیدر (کنترل می‌کند
    # که آیا اصلاً در لیست /telemetry/active-feeders قرار بگیرد و پایش شود یا نه).
    is_active = Column(Boolean, default=True)
    # is_online: وضعیت واقعی ارتباط (نتیجه آخرین Polling) که به‌صورت خودکار توسط
    # telemetry_service بر اساس موفقیت/شکست پی‌درپی به‌روزرسانی می‌شود. این فیلد از
    # is_active کاملاً مستقل است تا حتی وقتی یک فیدر آفلاین تشخیص داده می‌شود،
    # پایش آن متوقف نشود و امکان تشخیص خودکار بازگشت آن (recovery) باقی بماند.
    is_online = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- روابط ---
    post = relationship("Post", back_populates="feeders")

    __table_args__ = (
        Index('idx_feeder_post', 'post_id'),
    )
