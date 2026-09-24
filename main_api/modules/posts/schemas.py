from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

from main_api.modules.feeders.schemas import FeederResponse
from main_api.modules.locations.schemas import LocationResponse


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
