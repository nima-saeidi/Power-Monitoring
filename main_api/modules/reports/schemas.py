# app/reports/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

class TelemetryReportResponse(BaseModel):
    id: UUID
    post_id: int
    feeder_id: int
    key: str            # مثلاً voltage, current, power
    value: Any          # مقدار خوانده شده
    timestamp: datetime

    class Config:
        from_attributes = True


# گزارش‌های آماری برای نمودارها
class AggregatedReportResponse(BaseModel):
    feeder_id: int
    parameter: str          # مثلاً 'current_phase_a' یا 'active_power'
    avg_value: float
    max_value: float
    min_value: float
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True

# گزارش هشدارها و رویدادها
class AlertReportResponse(BaseModel):
    id: int
    post_id: int
    feeder_id: Optional[int]
    alert_type: str         # نوع هشدار (افت ولتاژ، قطع ارتباط و ...)
    message: str
    is_acknowledged: bool   # آیا اپراتور این هشدار را دیده/تایید کرده؟
    created_at: datetime

    class Config:
        from_attributes = True

# گزارش وضعیت لحظه‌ای پست‌ها برای داشبورد و نقشه
class PostStatusResponse(BaseModel):
    post_id: int
    post_name: str
    status: str             # 'normal', 'warning', 'offline'
    last_update: datetime

    class Config:
        from_attributes = True
