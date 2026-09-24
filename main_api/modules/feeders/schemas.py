from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.types import UUID4


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    feeder_type: Optional[str] = None
    max_current: Optional[float] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    modbus_address: Optional[int] = None
    active_power_register: Optional[int] = None
    reactive_power_register: Optional[int] = None
    voltage_register: Optional[int] = None
    current_register: Optional[int] = None
    power_factor_register: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_online: bool = True
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None


class FeederCreate(FeederBase):
    post_id: int


class FeederUpdate(BaseModel):
    name: Optional[str] = None
    feeder_type: Optional[str] = None
    max_current: Optional[float] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    modbus_address: Optional[int] = None
    active_power_register: Optional[int] = None
    reactive_power_register: Optional[int] = None
    voltage_register: Optional[int] = None
    current_register: Optional[int] = None
    power_factor_register: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    consecutive_failures: Optional[int] = None


class FeederResponse(FeederBase):
    id: int
    post_id: int

    model_config = ConfigDict(from_attributes=True)


# ----------------- Modbus Device -----------------
class CommandRequest(BaseModel):
    device_id: UUID4
    register_address: int
    command: bool
