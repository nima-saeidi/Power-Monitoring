from pydantic import BaseModel
from typing import Optional, List


# ----------------- Location Schemas -----------------
class LocationBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None


class LocationResponse(LocationBase):
    id: int

    model_config = {"from_attributes": True}


# ----------------- Feeder Schemas -----------------
class FeederBase(BaseModel):
    name: str
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    is_active: bool = True


class FeederCreate(FeederBase):
    post_id: int


class FeederUpdate(BaseModel):
    name: Optional[str] = None
    max_current: Optional[float] = None
    cable_type: Optional[str] = None
    is_active: Optional[bool] = None


class FeederResponse(FeederBase):
    id: int
    post_id: int

    model_config = {"from_attributes": True}


# ----------------- Post Schemas -----------------
class PostBase(BaseModel):
    name: str
    location_id: Optional[int] = None  # فیلد متنی قدیمی حذف و با کلید خارجی جایگزین شد
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool = True


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    name: Optional[str] = None
    location_id: Optional[int] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: Optional[bool] = None


class PostResponse(PostBase):
    id: int
    feeders: List[FeederResponse] = []
    location: Optional[LocationResponse] = None  # در صورت نیاز به نمایش اطلاعات مکان همراه پست

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}
