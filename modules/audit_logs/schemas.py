from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class AuditLogBase(BaseModel):
    """Schema پایه برای Audit Log"""
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    description: Optional[str] = None
    severity: str = 'info'


class AuditLogResponse(BaseModel):
    """Schema پاسخ Audit Log"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    user_role: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    description: Optional[str]
    changes: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    severity: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema پاسخ لیست Audit Logs"""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditLogFilterParams(BaseModel):
    """پارامترهای فیلتر برای Audit Logs"""
    user_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    severity: Optional[str] = Field(None, pattern='^(debug|info|warning|error|critical)$')
    success: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class CommandLogBase(BaseModel):
    """Schema پایه برای Command Log"""
    command_type: str
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class CommandLogResponse(BaseModel):
    """Schema پاسخ Command Log"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    ip_address: Optional[str]
    command_type: str
    post_id: Optional[int]
    feeder_id: Optional[int]
    target: Optional[str]
    parameters: Optional[Dict[str, Any]]
    modbus_function: Optional[int]
    register_address: Optional[int]
    success: bool
    response: Optional[str]
    response_time_ms: Optional[int]
    error_message: Optional[str]
    error_code: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CommandLogListResponse(BaseModel):
    """Schema پاسخ لیست Command Logs"""
    items: List[CommandLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CommandLogFilterParams(BaseModel):
    """پارامترهای فیلتر برای Command Logs"""
    post_id: Optional[int] = None
    feeder_id: Optional[int] = None
    user_id: Optional[int] = None
    command_type: Optional[str] = None
    success: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class UserActivityResponse(BaseModel):
    """پاسخ فعالیت‌های کاربر"""
    user_id: int
    username: str
    total_actions: int
    successful_actions: int
    failed_actions: int
    recent_logs: List[AuditLogResponse]
    period_days: int
