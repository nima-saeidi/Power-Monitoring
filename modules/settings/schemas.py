from pydantic import BaseModel, Field
from typing import Optional

class SettingUpdate(BaseModel):
    critical_threshold: Optional[float] = Field(None, ge=0.0, description="ضریب آلفا")
    warning_threshold: Optional[float] = Field(None, ge=0.0, description="ضریب بتا")
    access_token_expire_minutes: Optional[int] = Field(None, gt=0, description="مدت اعتبار توکن دسترسی به دقیقه")
    session_timeout_minutes: Optional[int] = Field(None, gt=0, description="مدت زمان تایم‌اوت شدن نشست (Session) به دقیقه")
    polling_interval: Optional[int] = Field(None, gt=0, description="بازه زمانی نمونه‌برداری (Polling) از دستگاه‌ها به ثانیه")
    max_telemetry_failures: Optional[int] = Field(None, ge=1, description="حداکثر تعداد خطاهای مجاز تله‌متری پیش از هشدار")
    max_login_attempts: Optional[int] = Field(None, ge=1, description="حداکثر تعداد تلاش‌های ناموفق مجاز برای ورود")
    data_retention_days: Optional[int] = Field(None, ge=1, description="تعداد روزهای نگهداری داده‌های تاریخچه‌ای (Retention)")

class SettingResponse(BaseModel):
    id: int
    critical_threshold: float
    warning_threshold: float
    access_token_expire_minutes: int
    session_timeout_minutes: int
    polling_interval: int
    max_telemetry_failures: int
    max_login_attempts: int
    data_retention_days: int

    class Config:
        from_attributes = True