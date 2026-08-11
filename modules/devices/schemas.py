from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pydantic.types import UUID4
# ----------------- Location Schemas -----------------
class LocationBase(BaseModel):
    name: str
    location_type: Optional[str] = None  # اضافه شده بر اساس مدل
    parent_id: Optional[int] = None
    description: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None

class LocationResponse(LocationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    modbus_address: Optional[int] = None  # اضافه شده بر اساس مدل
    metadata_info: Optional[Dict[str, Any]] = None  # برای دیتای JSONB
    is_active: bool = True

class FeederCreate(FeederBase):
    post_id: int

class FeederUpdate(BaseModel):
    name: Optional[str] = None
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
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: int = 502  # دیفالت پورت مادباس اضافه شد
    metadata_info: Optional[Dict[str, Any]] = None  # برای دیتای JSONB
    is_active: bool = True

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    name: Optional[str] = None
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class PostResponse(PostBase):
    id: int
    feeders: List[FeederResponse] = []
    location: Optional[LocationResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ----------------- Link Schemas -----------------
class LinkBase(BaseModel):
    name: str
    from_post_id: int
    to_post_id: int
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None

class LinkCreate(LinkBase):
    pass

class LinkUpdate(BaseModel):
    name: Optional[str] = None
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None

class LinkResponse(LinkBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


#----------------modbus device --------------------

class CommandRequest(BaseModel):
    device_id: UUID4       
    register_address: int   
    command: bool          