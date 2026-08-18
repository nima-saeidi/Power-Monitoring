from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from pydantic.types import UUID4


# ----------------- Location Schemas -----------------

class LocationBase(BaseModel):
    name: str = Field(alias="campus_name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class LocationCreate(LocationBase):
    sub_sections: List[str] = Field(default_factory=list)


# این کلاس اضافه شد تا خطای ایمپورت در روتر برطرف شود و فرمت دقیق درخواستی را بگیرد
class CampusWithSubsectionsCreate(BaseModel):
    campus_name: str
    sub_sections: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, alias="campus_name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class LocationResponse(BaseModel):
    id: int
    campus_name: str  # <--- این فیلد باید campus_name باشد نه name
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sub_locations: List['LocationResponse'] = []

    class Config:
        from_attributes = True  # در Pydantic v2
        # orm_mode = True       # در Pydantic v1


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    modbus_address: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
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
    port: int = 502
    metadata_info: Optional[Dict[str, Any]] = None
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


# ----------------- Modbus Device -----------------
class CommandRequest(BaseModel):
    device_id: UUID4
    register_address: int
    command: bool


# بازسازی مدل‌های بازگشتی (فقط یک بار در انتهای فایل اجرا می‌شود)
LocationResponse.model_rebuild()
