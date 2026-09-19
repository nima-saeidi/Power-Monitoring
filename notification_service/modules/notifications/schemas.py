from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    ALL = "all"

class NotificationPayload(BaseModel):
    channel: NotificationChannel = Field(default=NotificationChannel.ALL, description="کانال ارسال پیام")
    title: str = Field(..., min_length=1, description="عنوان اعلان یا موضوع ایمیل")
    message: str = Field(..., min_length=1, description="متن اصلی اعلان")
    phone_numbers: Optional[List[str]] = Field(default_factory=list, description="لیست شماره موبایل‌ها")
    email_addresses: Optional[List[EmailStr]] = Field(default_factory=list, description="لیست آدرس‌های ایمیل")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="اطلاعات متادیتا نظیر Device ID یا سطح بحرانی بودن")
