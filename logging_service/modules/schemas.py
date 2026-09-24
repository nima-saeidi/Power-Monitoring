from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class LogCreate(BaseModel):
    service_name: Optional[str] = Field(default="main_api", description="Name of the microservice")
    action: str = Field(..., description="Action name e.g. USER_LOGIN, DEVICE_UPDATE")
    user_id: Optional[int] = Field(default=None, description="User ID if authenticated")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary payload and metadata")


class LogItem(BaseModel):
    id: int
    service_name: Optional[str] = None
    action: str
    user_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LogFilterRequest(BaseModel):
    service_name: Optional[str] = Field(default=None, description="Filter by service name")
    action: Optional[str] = Field(default=None, description="Filter by action")
    user_id: Optional[int] = Field(default=None, description="Filter by user ID")
    search: Optional[str] = Field(default=None, description="Search keyword in action/service")
    severity: Optional[str] = Field(default=None, description="Filter by details.severity (INFO/WARNING/ERROR/CRITICAL)")
    success: Optional[bool] = Field(default=None, description="Filter by details.success")
    start_date: Optional[datetime] = Field(default=None, description="Filter logs created at/after this time")
    end_date: Optional[datetime] = Field(default=None, description="Filter logs created at/before this time")
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class LogListResponse(BaseModel):
    total: int
    items: List[LogItem]


class LogFilterOptionsResponse(BaseModel):
    services: List[str]
    actions: List[str]
