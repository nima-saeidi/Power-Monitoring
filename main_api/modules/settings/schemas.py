# main_api/modules/settings/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SettingUpdate(BaseModel):
    # مقادیر آستانه
    critical_threshold: Optional[float] = Field(None, ge=0.0, description="آستانه بحرانی")
    warning_threshold: Optional[float] = Field(None, ge=0.0, description="آستانه هشدار")

    # تنظیمات احراز هویت
    access_token_expire_minutes: Optional[int] = Field(None, gt=0, description="مدت اعتبار توکن دسترسی (دقیقه)")
    max_login_attempts: Optional[int] = Field(None, ge=1, description="حداکثر تلاش ناموفق ورود")
    lockout_duration_minutes: Optional[int] = Field(None, ge=1, description="مدت قفل شدن حساب (دقیقه)")
    session_timeout_minutes: Optional[int] = Field(None, gt=0, description="Timeout نشست (دقیقه)")

    # تنظیمات Modbus و تله‌متری
    polling_interval: Optional[int] = Field(None, gt=0, description="فاصله Polling (ثانیه)")
    max_telemetry_failures: Optional[int] = Field(None, ge=1, description="حداکثر خطای مجاز تله‌متری")
    modbus_timeout: Optional[int] = Field(None, gt=0, description="Timeout Modbus (ثانیه)")
    modbus_retry_count: Optional[int] = Field(None, ge=0, description="تعداد تلاش مجدد Modbus")

    # تنظیمات نوتیفیکیشن
    notification_retry_attempts: Optional[int] = Field(None, ge=0, description="تعداد تلاش مجدد نوتیفیکیشن")
    notification_cooldown_seconds: Optional[int] = Field(None, ge=0,
                                                         description="فاصله زمانی ارسال مجدد نوتیفیکیشن مشابه (ثانیه)")

    # تنظیمات گزارش‌گیری
    report_generation_timeout: Optional[int] = Field(None, gt=0, description="Timeout تولید گزارش (ثانیه)")
    max_export_records: Optional[int] = Field(None, gt=0, description="حداکثر رکورد در Export")


class SettingResponse(BaseModel):
    id: int
    critical_threshold: float
    warning_threshold: float

    access_token_expire_minutes: int
    max_login_attempts: int
    lockout_duration_minutes: int
    session_timeout_minutes: int

    polling_interval: int
    max_telemetry_failures: int
    modbus_timeout: int
    modbus_retry_count: int

    notification_retry_attempts: int
    notification_cooldown_seconds: int

    report_generation_timeout: int
    max_export_records: int

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
