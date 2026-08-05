# modules/telemetry/schemas.py
from pydantic import BaseModel
from datetime import datetime

class TelemetryCreate(BaseModel):
    active_power: float
    reactive_power: float
    voltage: float
    current: float
    power_factor: float

class TelemetryResponse(TelemetryCreate):
    id: int
    feeder_id: int
    timestamp: datetime

    class Config:
        from_attributes = True
