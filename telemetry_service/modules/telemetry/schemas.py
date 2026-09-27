from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class TelemetryBase(BaseModel):

    feeder_id: int = Field(
        ...,
        description="شناسه فیدر",
    )

    post_id: Optional[str] = Field(
        default=None,
        description="شناسه پست، مانند POST_1",
    )

    voltage: float = Field(
        default=0.0,
        description="ولتاژ برحسب ولت",
    )

    current: float = Field(
        default=0.0,
        description="جریان برحسب آمپر",
    )

    active_power: float = Field(
        default=0.0,
        description="توان اکتیو برحسب کیلووات",
    )

    reactive_power: float = Field(
        default=0.0,
        description="توان راکتیو برحسب کیلووار",
    )

    power_factor: float = Field(
        default=1.0,
        description="ضریب توان",
    )

    frequency: Optional[float] = Field(
        default=50.0,
        description="فرکانس برحسب هرتز",
    )


class TelemetryCreate(TelemetryBase):

    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="زمان ثبت داده",
    )


class TelemetryResponse(TelemetryBase):

    timestamp: datetime = Field(
        ...,
        description="زمان داده",
    )

    model_config = ConfigDict(
        from_attributes=True,
    )


class TelemetryReportQuery(BaseModel):

    feeder_id: int = Field(
        ...,
        description="شناسه فیدر",
    )

    start_time: datetime = Field(
        ...,
        description="زمان شروع گزارش",
    )

    end_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="زمان پایان گزارش",
    )

    window_period: str = Field(
        default="1m",
        description="بازه میانگین‌گیری؛ مانند 10s، 1m، 5m یا 1h",
    )


class DeviceAlertSchema(BaseModel):

    feeder_id: int = Field(
        ...,
        description="شناسه فیدر",
    )

    status: str = Field(
        ...,
        description="وضعیت تجهیز: offline، deactivated یا online",
    )

    failures: int = Field(
        default=0,
        description="تعداد خطاها",
    )

    reason: str = Field(
        ...,
        description="علت هشدار",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="زمان هشدار",
    )


class ChartDataPoint(BaseModel):

    timestamp: Union[datetime, str] = Field(
        ...,
        description="زمان نقطه",
    )

    value: Optional[float] = Field(
        default=None,
        description="مقدار نقطه",
    )


class TelemetryChartResponse(BaseModel):

    feeder_id: int = Field(
        ...,
        description="شناسه فیدر",
    )

    series: Dict[str, List[ChartDataPoint]] = Field(
        default_factory=dict,
        description="سری‌های زمانی به تفکیک پارامتر",
    )
