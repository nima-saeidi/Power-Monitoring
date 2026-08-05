from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from modules.auth.models import RoleEnum

class AdminRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# مدل ساخت کاربر توسط ادمین (قابلیت تعیین نقش)
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.USER # کاربر عادی پیش‌فرض
    is_active: bool = True

# مدل ویرایش کاربر توسط ادمین (همه فیلدها اختیاری هستند)
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: RoleEnum | str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
