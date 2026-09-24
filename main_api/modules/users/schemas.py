from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional
from datetime import datetime
from main_api.modules.users.models import RoleEnum


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=50)
    role: RoleEnum = RoleEnum.USER
    is_active: bool = True
    sms_notification_enabled: bool = False # اضافه شد (پیش‌فرض: غیرفعال)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: Optional[str] = Field(default=None, min_length=6, max_length=50)
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    sms_notification_enabled: Optional[bool] = None # اضافه شد

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: RoleEnum | str
    is_active: bool
    sms_notification_enabled: bool | None = False  # در پایتون ۳.۱۰ به بالا
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
