from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from pydantic.types import UUID4

# ----------------- Location Schemas -----------------
class LocationBase(BaseModel):
    name: str
    location_type: Optional[str] = None  # مثال: Root, Campus, SubSection
    parent_id: Optional[int] = None
    description: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class CampusWithSubsectionsCreate(BaseModel):
    campus_name: str
    sub_sections: List[str] = []
    description: Optional[str] = None

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None

class LocationResponse(LocationBase):
    id: int
    sub_locations: List['LocationResponse'] = []

    model_config = ConfigDict(from_attributes=True)


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    feeder_type: Optional[str] = None  # اضافه شده: نوع فیدر (تولید کننده / مصرف کننده)
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    modbus_address: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True

class FeederCreate(FeederBase):
    post_id: int

class FeederUpdate(BaseModel):
    name: Optional[str] = None
    feeder_type: Optional[str] = None
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    modbus_address: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class FeederResponse(FeederBase):
    id: int
    post_id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- Post Schemas -----------------
class PostBase(BaseModel):
    name: str
    supply_source: Optional[str] = None  # اضافه شده: محل تغذیه
    campus_id: Optional[int] = None      # اضافه شده: پردیس
    unit_id: Optional[int] = None        # اضافه شده: واحد
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: int = 502
    latitude: Optional[float] = None     # اضافه شده: عرض جغرافیایی
    longitude: Optional[float] = None    # اضافه شده: طول جغرافیایی
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: bool = True

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    name: Optional[str] = None
    supply_source: Optional[str] = None
    campus_id: Optional[int] = None
    unit_id: Optional[int] = None
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class PostResponse(PostBase):
    id: int
    feeders: List[FeederResponse] = []
    location: Optional[LocationResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ----------------- Link Schemas -----------------
class LinkBase(BaseModel):
    name: Optional[str] = None  # در مدل دیتابیس nullable=True است
    from_post_id: int
    to_post_id: int
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None
    length: Optional[float] = None  # اضافه شده: طول لینک
    metadata_info: Optional[Dict[str, Any]] = None  # اضافه شده: اطلاعات دینامیک
    is_active: bool = True  # اضافه شده: وضعیت فعال بودن

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
