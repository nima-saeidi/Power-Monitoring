from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from modules.notifications.models import NotificationType, NotificationPriority


# ============= Response Schemas =============

class NotificationResponse(BaseModel):
    """پاسخ نوتیفیکیشن"""
    id: int
    user_id: int
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    source_type: Optional[str]
    source_id: Optional[int]
    metadata: Optional[Dict[str, Any]]
    is_read: bool
    read_at: Optional[datetime]
    is_dismissed: bool
    dismissed_at: Optional[datetime]
    action_url: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """پاسخ لیست نوتیفیکیشن‌ها"""
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    """پاسخ تنظیمات نوتیفیکیشن"""
    id: int
    user_id: int
    enable_info: bool
    enable_warning: bool
    enable_error: bool
    enable_success: bool
    enable_alert: bool
    min_priority: NotificationPriority
    auto_dismiss_after_read: bool
    auto_dismiss_delay_minutes: Optional[int]
    max_display_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============= Request Schemas =============

class NotificationCreateRequest(BaseModel):
    """درخواست ایجاد نوتیفیکیشن"""
    user_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.MEDIUM
    source_type: Optional[str] = Field(None, max_length=50)
    source_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class NotificationBulkCreateRequest(BaseModel):
    """درخواست ایجاد دسته‌ای نوتیفیکیشن"""
    user_ids: List[int] = Field(..., min_items=1)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.MEDIUM
    source_type: Optional[str] = Field(None, max_length=50)
    source_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class NotificationPreferenceUpdateRequest(BaseModel):
    """درخواست به‌روزرسانی تنظیمات"""
    enable_info: Optional[bool] = None
    enable_warning: Optional[bool] = None
    enable_error: Optional[bool] = None
    enable_success: Optional[bool] = None
    enable_alert: Optional[bool] = None
    min_priority: Optional[NotificationPriority] = None
    auto_dismiss_after_read: Optional[bool] = None
    auto_dismiss_delay_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_display_count: Optional[int] = Field(None, ge=10, le=500)


class NotificationMarkReadRequest(BaseModel):
    """درخواست علامت‌گذاری به عنوان خوانده شده"""
    notification_ids: List[int] = Field(..., min_items=1)


# ============= Filter Schemas =============

class NotificationFilterParams(BaseModel):
    """پارامترهای فیلتر نوتیفیکیشن‌ها"""
    unread_only: bool = False
    include_dismissed: bool = False
    type: Optional[NotificationType] = None
    priority: Optional[NotificationPriority] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)
