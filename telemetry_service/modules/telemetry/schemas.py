from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class TelemetryBase(BaseModel):
    """مدل پایه داده‌های ۵ گانه الکتریکی فیدر"""
    feeder_id: int
    post_id: Optional[int] = None
    voltage: float = Field(default=0.0, description="ولتاژ (V)")
    current: float = Field(default=0.0, description="جریان (A)")
    active_power: float = Field(default=0.0, description="توان اکتیو (kW)")
    reactive_power: float = Field(default=0.0, description="توان راکتیو (kVAR)")
    power_factor: float = Field(default=1.0, description="ضریب توان (PF)")
    frequency: Optional[float] = Field(default=50.0, description="فرکانس (Hz)")


class TelemetryCreate(TelemetryBase):
    """مدل ورودی جهت ثبت در InfluxDB"""
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TelemetryResponse(TelemetryBase):
    """مدل خروجی برای وب‌سوکت، API و کلاینت‌ها"""
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryReportQuery(BaseModel):
    """فیلترهای گزارش‌گیری بازه زمانی"""
    feeder_id: int
    start_time: datetime
    end_time: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    window_period: Optional[str] = Field(default="1m", description="بازه میانگین‌گیری (e.g., 10s, 1m, 5m, 1h)")


class DeviceAlertSchema(BaseModel):
    """مدل انتشار آلرت‌های وضعیت تجهیزات"""
    feeder_id: int
    status: str  # offline | deactivated | online
    failures: int
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChartDataPoint(BaseModel):
    timestamp: datetime | str
    value: Optional[float]

class TelemetryChartResponse(BaseModel):
    feeder_id: int
    series: Dict[str, List[ChartDataPoint]]