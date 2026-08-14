from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.sql import func
from main_api.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # مقادیر آستانه (جایگزین آلفا و بتا)
    critical_threshold = Column(Float, default=90.0, nullable=False, comment="آستانه بحرانی (Critical Threshold)")
    warning_threshold = Column(Float, default=75.0, nullable=False, comment="آستانه هشدار (Warning Threshold)")

    # تنظیمات احراز هویت
    access_token_expire_minutes = Column(Integer, default=1440, nullable=False,
                                         comment="مدت اعتبار Access Token (دقیقه)")
    refresh_token_expire_days = Column(Integer, default=7, nullable=False, comment="مدت اعتبار Refresh Token (روز)")
    max_login_attempts = Column(Integer, default=5, nullable=False, comment="حداکثر تلاش ناموفق ورود")
    lockout_duration_minutes = Column(Integer, default=30, nullable=False, comment="مدت قفل شدن حساب (دقیقه)")
    session_timeout_minutes = Column(Integer, default=120, nullable=False, comment="Timeout نشست (دقیقه)")

    # تنظیمات Modbus و تله‌متری
    polling_interval = Column(Integer, default=5, nullable=False, comment="فاصله Polling (ثانیه)")
    max_telemetry_failures = Column(Integer, default=3, nullable=False, comment="حداکثر خطای مجاز تله‌متری")
    modbus_timeout = Column(Integer, default=3, nullable=False, comment="Timeout Modbus (ثانیه)")
    modbus_retry_count = Column(Integer, default=3, nullable=False, comment="تعداد تلاش مجدد Modbus")
    connection_pool_size = Column(Integer, default=10, nullable=False, comment="اندازه Pool اتصالات")

    # تنظیمات نگهداری داده
    data_retention_days = Column(Integer, default=365, nullable=False, comment="مدت نگهداری داده‌های تله‌متری (روز)")
    log_retention_days = Column(Integer, default=90, nullable=False, comment="مدت نگهداری لاگ‌ها (روز)")
    audit_log_retention_days = Column(Integer, default=180, nullable=False, comment="مدت نگهداری لاگ‌های Audit (روز)")

    # تنظیمات نوتیفیکیشن
    notification_batch_size = Column(Integer, default=100, nullable=False, comment="تعداد نوتیفیکیشن در هر Batch")
    notification_retry_attempts = Column(Integer, default=3, nullable=False, comment="تعداد تلاش مجدد نوتیفیکیشن")
    notification_cooldown_seconds = Column(Integer, default=300, nullable=False,
                                           comment="فاصله زمانی ارسال مجدد نوتیفیکیشن مشابه (ثانیه)")

    # تنظیمات گزارش‌گیری
    report_generation_timeout = Column(Integer, default=300, nullable=False, comment="Timeout تولید گزارش (ثانیه)")
    max_export_records = Column(Integer, default=10000, nullable=False, comment="حداکثر رکورد در Export")

    # تنظیمات کلی سیستم
    system_name = Column(String(100), default="Power Monitoring System", nullable=False, comment="نام سیستم")
    system_timezone = Column(String(50), default="Asia/Tehran", nullable=False, comment="منطقه زمانی")
    maintenance_mode = Column(Boolean, default=False, nullable=False, comment="وضعیت تعمیر و نگهداری")

    # متادیتا
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
