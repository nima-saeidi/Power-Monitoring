from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


# ۱. مدل پایه: فقط فیلدهایی که موقع ثبت و دریافت مشترک هستند (بدون id)
class TelemetryBase(BaseModel):
    post_id: Optional[int] = None
    feeder_id: Optional[int] = None
    key: str  
    value_int: Optional[int] = None
    value_bool: Optional[bool] = None

# ۲. مدل Create: برای دریافت داده از سمت سنسور/کلاینت (id توسط دیتابیس ساخته می‌شود)
class TelemetryCreate(TelemetryBase):
    pass

# ۳. مدل Response: برای ارسال داده به کلاینت (id و timestamp اضافه می‌شوند)
class TelemetryResponse(TelemetryBase):
    id: int    # 👈 نوع id به UUID اصلاح شد
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
