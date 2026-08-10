from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TelemetryBase(BaseModel):
    post_id: Optional[int] = None     # 👈 تغییر به Optional
    feeder_id: Optional[int] = None   # 👈 اضافه شدن فیدر برای پشتیبانی از دیتای فیدرها
    key: str  
    value_int: Optional[int] = None
    value_float: Optional[float] = None
    value_str: Optional[str] = None   # (اگر در دیتابیس value_string است، این را تغییر دهید)
    value_bool: Optional[bool] = None

class TelemetryCreate(TelemetryBase):
    pass

class TelemetryResponse(TelemetryBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
