from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr

class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    ALL = "all"

class NotificationPayload(BaseModel):
    channel: NotificationChannel
    title: str
    message: str
    phone_numbers: Optional[List[str]] = []
    email_addresses: Optional[List[EmailStr]] = []
    metadata: Optional[dict] = {}  # برای نگهداری اطلاعات اضافه مثل device_id, severity و ...
