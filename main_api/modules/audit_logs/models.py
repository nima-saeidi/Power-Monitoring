# main_api/modules/logs/models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from main_api.core.database import Base


class AuditLog(Base):
    """
    جدول لاگ‌های حسابرسی (Audit)
    برای ثبت ورود، خروج، تغییرات مهم در سیستم و رفتار کاربران
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # ثبت زمان دقیق با پشتیبانی از Timezone
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # اطلاعات کاربر (با SET NULL برای حفظ لاگ حتی در صورت حذف کاربر)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=True)  # Snapshot
    user_role = Column(String(20), nullable=True)  # Snapshot

    # اطلاعات کلاینت
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # اطلاعات عملیات
    action = Column(String(100), index=True, nullable=False)  # مثلا: LOGIN, DELETE_USER, UPDATE_SETTINGS
    resource_type = Column(String(50), index=True, nullable=True)  # مثلا: User, Feeder, Setting
    resource_id = Column(String(50), nullable=True)  # آیدی رکوردی که تغییر کرده
    description = Column(String(255), nullable=True)

    # استفاده از JSON استاندارد که در SQLite هم به خوبی کار می‌کند
    changes = Column(JSON, nullable=True)  # ذخیره مقادیر قبل و بعد از تغییر
    meta_data = Column(JSON, nullable=True)  # دیتای اضافی (مثلا هدرها)

    # وضعیت عملیات
    success = Column(Boolean, default=True)
    error_message = Column(String(500), nullable=True)
    severity = Column(String(20), default="INFO")  # INFO, WARNING, ERROR, CRITICAL


class CommandLog(Base):
    """
    جدول لاگ‌های دستورات Modbus و سخت‌افزاری
    """
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # کاربری که دستور را ارسال کرده
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # نوع و هدف دستور
    command_type = Column(String(50), index=True, nullable=False)  # read, write, control, config
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="SET NULL"), nullable=True)
    target = Column(String(100), nullable=True)  # نام یا IP دستگاه هدف

    # جزئیات دستور Modbus
    parameters = Column(JSON, nullable=True)  # مقادیر ارسالی
    modbus_function = Column(Integer, nullable=True)  # کد فانکشن مادباس (مثلا 3 یا 6)
    register_address = Column(Integer, nullable=True)

    # نتیجه
    success = Column(Boolean, default=True, index=True)
    response = Column(JSON, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)


class DeviceTestLog(Base):
    """
    جدول لاگ تست‌های ارتباطی (Ping / Connection Test)
    """
    __tablename__ = "device_test_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    tested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # CASCADE استفاده شده تا اگر پست/فیدر پاک شد، لاگ تست‌های تکراری آن هم پاک شود (اختیاری)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), nullable=True)

    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)

    test_type = Column(String(50), index=True, nullable=False)  # ping, modbus, connection

    success = Column(Boolean, default=True)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)
