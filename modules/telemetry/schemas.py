from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TelemetryBase(BaseModel):
    post_id: int
    parameter_name: str  # مثلاً 'voltage_phase_a'
    value_int: Optional[int] = None
    value_float: Optional[float] = None
    value_str: Optional[str] = None
    value_bool: Optional[bool] = None

class TelemetryCreate(TelemetryBase):
    pass

class TelemetryResponse(TelemetryBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
