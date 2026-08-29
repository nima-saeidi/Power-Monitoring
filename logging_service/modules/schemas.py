from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class LogFilterRequest(BaseModel):
    query: Optional[str] = Field(default="*", description="Lucene query e.g. level:3 OR service_name:main_api")
    range_seconds: int = Field(default=86400, description="Range in seconds, default 24 hours (86400)")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

class LogItem(BaseModel):
    id: str
    timestamp: datetime
    message: str
    level: Optional[int] = None
    service_name: Optional[str] = None
    source: Optional[str] = None
    extra_fields: Dict[str, Any] = Field(default_factory=dict)

class LogListResponse(BaseModel):
    total: int
    items: List[LogItem]
