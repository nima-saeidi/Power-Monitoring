from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.sql import func
from main_api.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    critical_threshold = Column(Float, default=90.0, nullable=False, comment="آستانه بحرانی (Critical Threshold)")
    warning_threshold = Column(Float, default=75.0, nullable=False, comment="آستانه هشدار (Warning Threshold)")

    access_token_expire_minutes = Column(Integer, default=20, nullable=False,
                                         comment="مدت اعتبار Access Token (دقیقه)")
    max_login_attempts = Column(Integer, default=5, nullable=False, comment="حداکثر تلاش ناموفق ورود")
    lockout_duration_minutes = Column(Integer, default=30, nullable=False, comment="مدت قفل شدن حساب (دقیقه)")
    session_timeout_minutes = Column(Integer, default=120, nullable=False, comment="Timeout نشست (دقیقه)")

    polling_interval = Column(Integer, default=5, nullable=False, comment="فاصله Polling (ثانیه)")
    max_telemetry_failures = Column(Integer, default=3, nullable=False, comment="حداکثر خطای مجاز تله‌متری")
    modbus_timeout = Column(Integer, default=3, nullable=False, comment="Timeout Modbus (ثانیه)")
    modbus_retry_count = Column(Integer, default=3, nullable=False, comment="تعداد تلاش مجدد Modbus")
    feeder_offline_retry_interval = Column(
        Integer, default=300, nullable=False,
        comment="فاصله تست مجدد فیدری که آفلاین تشخیص داده شده (ثانیه) — پیش‌فرض ۵ دقیقه"
    )

    notification_retry_attempts = Column(Integer, default=3, nullable=False, comment="تعداد تلاش مجدد نوتیفیکیشن")
    notification_cooldown_seconds = Column(Integer, default=300, nullable=False,
                                           comment="فاصله زمانی ارسال مجدد نوتیفیکیشن مشابه (ثانیه)")

    report_generation_timeout = Column(Integer, default=300, nullable=False, comment="Timeout تولید گزارش (ثانیه)")
    max_export_records = Column(Integer, default=10000, nullable=False, comment="حداکثر رکورد در Export")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
