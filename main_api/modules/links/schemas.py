from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

from main_api.modules.posts.schemas import PostResponse


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
    # اضافه‌کردن روابط برای نمایش اطلاعات کامل پست مبدأ و مقصد
    from_post: Optional[PostResponse] = None
    to_post: Optional[PostResponse] = None

    model_config = ConfigDict(from_attributes=True)
