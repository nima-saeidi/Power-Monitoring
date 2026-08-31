from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TelemetryBase(BaseModel):
    device_id: str
    active_power: float
    reactive_power: float
    voltage: float
    current: float
    power_factor: float
    frequency: Optional[float] = 50.0

class TelemetryCreate(TelemetryBase):
    pass

class TelemetryResponse(TelemetryBase):
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- ساختار اطلاعات ارسالی به شِدولر/ورکر تلمتری ---
class ActiveFeederConfig(BaseModel):
    feeder_id: int
    post_id: int
    name: str
    ip_address: str
    port: int = 502
    slave_id: int = 1
    scan_interval: int = 5
    is_active: bool = True

    class Config:
        from_attributes = True
