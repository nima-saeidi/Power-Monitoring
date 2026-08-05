from pydantic import BaseModel
from typing import Optional, List

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
    location: Optional[str] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool = True

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    transformer_specs: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: Optional[bool] = None

class PostResponse(PostBase):
    id: int
    feeders: List[FeederResponse] = []

    model_config = {"from_attributes": True}
