from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ----------------- Location Schemas -----------------
class LocationFlatResponse(BaseModel):
    id: int
    campus_name: Optional[str] = Field(default=None, validation_alias="name")
    location_type: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

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


LocationResponse.model_rebuild()
