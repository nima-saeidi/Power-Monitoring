from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TelemetryBase(BaseModel):
    """مدل پایه داده‌های الکتریکی فیدر"""
    feeder_id: int
    post_id: Optional[int] = None
    voltage: float = Field(default=0.0, description="Voltage in Volts")
    current: float = Field(default=0.0, description="Current in Amperes")
    active_power: float = Field(default=0.0, description="Active Power in Watts/kW")
    frequency: Optional[float] = Field(default=50.0, description="Frequency in Hz")


class TelemetryCreate(TelemetryBase):
    """مدل ورودی جهت ثبت در InfluxDB"""
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TelemetryResponse(TelemetryBase):
    """مدل خروجی جهت ارسال به وب‌سوکت یا کلاینت‌ها"""
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceAlertSchema(BaseModel):
    """مدل انتشار آلرت‌های وضعیت تجهیزات"""
    feeder_id: int
    status: str  # offline | deactivated | online
    failures: int
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
