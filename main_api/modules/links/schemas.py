from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

from main_api.modules.posts.schemas import PostResponse


class LinkBase(BaseModel):
    name: Optional[str] = None
    from_post_id: int
    to_post_id: int
    cable_type: Optional[str] = None
    cross_section: Optional[float] = None
    allowed_current: Optional[float] = None
    length: Optional[float] = None
    feeder_id: Optional[int] = None
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
    feeder_id: Optional[int] = None
    metadata_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class LinkResponse(LinkBase):
    id: int
    load_status: str = "unknown"
    from_post: Optional[PostResponse] = None
    to_post: Optional[PostResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ActiveLinkSource(BaseModel):
    """Internal contract for link_ingestion_service.

    The external source of a link is configured in its metadata under the
    `external_source` key, e.g.:
        {"external_source": {"provider": "http", "external_id": "LNK-17",
                             "interval": 60, "field_map": {"current": "data.i"}}}
    """
    link_id: int
    name: Optional[str] = None
    feeder_id: Optional[int] = None
    allowed_current: Optional[float] = None
    provider: str
    external_id: str
    interval: Optional[int] = None
    field_map: Dict[str, str] = {}
    options: Dict[str, Any] = {}
