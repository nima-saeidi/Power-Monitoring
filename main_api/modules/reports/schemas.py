# app/reports/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
# اگر id در دیتابیس شما عدد صحیح است، UUID را حذف کنید (در اینجا int فرض شده است)

class TelemetryReportResponse(BaseModel):
    id: int  # یا UUID
    post_id: Optional[int] = None
    feeder_id: int
    key: str
    value_int: Optional[float] = None  # مقدار عددی (ولتاژ، جریان و ...)
    value_bool: Optional[bool] = None  # مقدار منطقی (وضعیت کلیدها)
    timestamp: datetime

    class Config:
        from_attributes = True

class AggregatedReportResponse(BaseModel):
    feeder_id: int
    parameter: str
    avg_value: Optional[float]
    max_value: Optional[float]
    min_value: Optional[float]
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True

class AlertReportResponse(BaseModel):
    id: int
    post_id: int
    feeder_id: Optional[int]
    alert_type: str
    message: str
    is_acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PostStatusResponse(BaseModel):
    post_id: int
    post_name: str
    status: str
    last_update: datetime

    class Config:
        from_attributes = True
