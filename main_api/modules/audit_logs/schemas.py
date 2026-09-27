from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field



class AuditLogBase(BaseModel):
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    description: Optional[str] = None
    severity: str = 'INFO'


class AuditLogResponse(BaseModel):
    id: int
    service_name: Optional[str] = None
    action: str
    user_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UserActivityResponse(BaseModel):
    user_id: int
    total_actions: int
    successful_actions: int
    failed_actions: int
    recent_logs: List[AuditLogResponse]
    period_days: int



class CommandLogResponse(BaseModel):
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
    response: Optional[Dict[str, Any]]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    error_code: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class CommandLogListResponse(BaseModel):
    items: List[CommandLogResponse]
    total: int
    page: int
    page_size: int
    pages: int



class DeviceTestLogResponse(BaseModel):
    id: int
    timestamp: datetime
    tested_by_user_id: Optional[int]
    post_id: Optional[int]
    feeder_id: Optional[int]
    device_name: Optional[str]
    ip_address: Optional[str]
    port: Optional[int]
    test_type: str
    success: bool
    response_time_ms: Optional[float]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DeviceTestLogListResponse(BaseModel):
    items: List[DeviceTestLogResponse]
    total: int
    page: int
    page_size: int
    pages: int
