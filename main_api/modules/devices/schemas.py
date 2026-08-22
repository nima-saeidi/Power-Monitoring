from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from pydantic.types import UUID4


# ----------------- Location Schemas -----------------

class LocationBase(BaseModel):
    name: str = Field(alias="campus_name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class LocationCreate(LocationBase):
    sub_sections: List[str] = Field(default_factory=list)


class CampusWithSubsectionsCreate(BaseModel):
    campus_name: str
    sub_sections: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    address: Optional[str] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, alias="campus_name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class LocationResponse(BaseModel):
    id: int
    campus_name: Optional[str] = Field(default=None, validation_alias="name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    address: Optional[str] = None
    sub_locations: List['LocationResponse'] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    consecutive_failures: int = 0


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


# ----------------- Post Schemas -----------------
class PostBase(BaseModel):
    name: str
    supply_source: Optional[str] = None
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: int = 502
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True
    consecutive_failures: int = 0


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    name: Optional[str] = None
    supply_source: Optional[str] = None
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    consecutive_failures: Optional[int] = None


class PostResponse(PostBase):
    id: int
    feeders: List[FeederResponse] = []
    location: Optional[LocationResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------- Link Schemas -----------------
class LinkBase(BaseModel):
    name: Optional[str] = None
    from_post_id: int
    to_post_id: int
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None
    length: Optional[float] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True


class LinkCreate(LinkBase):
    pass


class LinkUpdate(BaseModel):
    name: Optional[str] = None
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None
    length: Optional[float] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LinkResponse(LinkBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ----------------- Modbus Device -----------------
class CommandRequest(BaseModel):
    device_id: UUID4
    register_address: int
    command: bool


# بازسازی مدل‌های بازگشتی
LocationResponse.model_rebuild()
