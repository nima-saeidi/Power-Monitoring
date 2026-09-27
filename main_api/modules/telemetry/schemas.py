from pydantic import BaseModel, Field
from typing import Dict, Optional, List
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

class ActiveFeederConfig(BaseModel):
    feeder_id: int
    post_id: int
    name: str
    ip_address: str
    port: int = 502
    slave_id: int = 1
    scan_interval: int = 5
    max_failures: int = 3
    modbus_timeout: int = 3
    modbus_retry_count: int = 3
    offline_retry_interval: int = 300
    is_active: bool = True
    is_online: bool = True
    active_power_register: Optional[int] = None
    reactive_power_register: Optional[int] = None
    voltage_register: Optional[int] = None
    current_register: Optional[int] = None
    power_factor_register: Optional[int] = None
    register_scales: Dict[str, float] = {}
    signed_registers: List[str] = []

    class Config:
        from_attributes = True


class FeederStatusUpdate(BaseModel):
    feeder_id: int
    is_online: bool
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    status_changed: bool = False
