from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional
from datetime import datetime
from main_api.modules.auth.models import RoleEnum

class AdminRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=50)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=50)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=50)
    role: RoleEnum = RoleEnum.USER
    is_active: bool = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: Optional[str] = Field(default=None, min_length=6, max_length=50)
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)

# اسکماهای جدید تغییر رمز عبور
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=50, description="رمز عبور فعلی")
    new_password: str = Field(..., min_length=6, max_length=50, description="رمز عبور جدید")

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: RoleEnum | str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
# برای دریافت ایمیل از کاربر
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="ایمیل ثبت نامی کاربر")

# برای ثبت رمز جدید با استفاده از توکن
class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="توکن ارسال شده به ایمیل")
    new_password: str = Field(..., min_length=6, max_length=50, description="رمز عبور جدید")
