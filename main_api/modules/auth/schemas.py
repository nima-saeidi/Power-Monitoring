from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from main_api.modules.users.schemas import UserResponse

class AdminRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=50)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=50)

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)

# اسکماهای تغییر رمز عبور
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=50, description="رمز عبور فعلی")
    new_password: str = Field(..., min_length=6, max_length=50, description="رمز عبور جدید")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int            # مدت زمان اعتبار توکن به ثانیه
    expires_at: datetime       # زمان دقیق منقضی شدن توکن

# برای دریافت ایمیل از کاربر
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str
    session_token: str  # توکن موقت حاوی هش کد جهت اعتبارسنجی مرحله بعد

class VerifyCodeRequest(BaseModel):
    code: str
    session_token: str

class VerifyCodeResponse(BaseModel):
    message: str
    reset_token: str  # توکن مجاز برای تغییر رمز

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str
