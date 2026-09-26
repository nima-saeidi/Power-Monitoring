from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator

from main_api.core.domain import PAGES
from typing import List, Optional
from datetime import datetime
from main_api.modules.users.models import RoleEnum


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=50)
    role: RoleEnum = RoleEnum.USER
    is_active: bool = True
    # دریافت هشدارها (قطعی، هشدار، بحرانی) با ایمیل؛ نام فیلد برای سازگاری با نسخه‌ی قبل حفظ شده
    sms_notification_enabled: bool = False
    # صفحه‌های مجاز این حساب (کلیدهای GET /users/pages/list)؛ خالی یعنی همه
    allowed_pages: Optional[List[str]] = None

    @field_validator("allowed_pages")
    @classmethod
    def _validate_pages(cls, value):
        if value is None:
            return None
        unknown = [p for p in value if p not in PAGES]
        if unknown:
            raise ValueError(f"صفحه‌ی نامعتبر: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: Optional[str] = Field(default=None, min_length=6, max_length=50)
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    sms_notification_enabled: Optional[bool] = None
    allowed_pages: Optional[List[str]] = None

    @field_validator("allowed_pages")
    @classmethod
    def _validate_pages(cls, value):
        if value is None:
            return None
        unknown = [p for p in value if p not in PAGES]
        if unknown:
            raise ValueError(f"صفحه‌ی نامعتبر: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: RoleEnum | str
    is_active: bool
    sms_notification_enabled: bool | None = False
    allowed_pages: Optional[List[str]] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
