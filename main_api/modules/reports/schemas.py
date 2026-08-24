from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TelemetryReportResponse(BaseModel):
    id: int
    post_id: Optional[int] = None
    feeder_id: int
    key: str
    value_int: Optional[float] = None  # مقدار عددی (مثل توان، ولتاژ، جریان)
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


class ChartDataPoint(BaseModel):
    timestamp: datetime
    value: Optional[float] = None

# مدل‌های قبلی که داشتید سر جایش می‌ماند
class AggregatedReportResponse(BaseModel):
    feeder_id: int
    parameter: str
    avg_value: Optional[float]
    max_value: Optional[float]
    min_value: Optional[float]
    start_date: datetime
    end_date: datetime