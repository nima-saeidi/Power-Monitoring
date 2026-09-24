from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.database import get_db
from main_api.core.broker import get_rabbitmq_publisher, RabbitMQPublisher
from main_api.modules.users.repository import UserRepository
from main_api.modules.auth.service import AuthService
from main_api.modules.auth.dependencies import get_current_user
from main_api.modules.auth.schemas import (
    AdminRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfileUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyCodeRequest,
)
from main_api.modules.users.schemas import UserResponse

auth_router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_rabbitmq_publisher),
) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repository=repo, publisher=publisher, db=db)


@auth_router.post(
    "/register-admin",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register Initial Admin",
)
async def register_admin(
    data: AdminRegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    """ثبت‌نام ادمین اولیه: رویداد ایجاد به صف ارسال می‌شود."""
    return await service.register_admin(data)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and Get Token",
)
async def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    """ورود کاربر و دریافت توکن دسترسی داینامیک"""
    return await service.login(data)


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Personal Profile",
)
async def get_my_profile(
    current_user=Depends(get_current_user),
):
    """دریافت اطلاعات پروفایل کاربر لاگین‌شده"""
    return current_user


@auth_router.put(
    "/me",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Update Personal Profile",
)
async def update_my_profile(
    data: UserProfileUpdate,
    current_user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """به‌روزرسانی پروفایل کاربر فعلی (ارسال به صف)"""
    return await service.update_profile(current_user.id, data)


@auth_router.post(
    "/change-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Change Password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """تغییر رمز عبور توسط کاربر لاگین‌شده"""
    return await service.change_password(current_user.id, data)


@auth_router.post(
    "/forgot-password",
    summary="Request Password Reset Code",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
):
    """درخواست ارسال کد بازیابی رمز عبور به ایمیل"""
    return await service.forgot_password(data, background_tasks)


@auth_router.post(
    "/verify-reset-code",
    summary="Verify Password Reset Code",
)
async def verify_reset_code(
    data: VerifyCodeRequest,
    service: AuthService = Depends(get_auth_service),
):
    """بررسی کد OTP و دریافت reset_token نهایی"""
    return await service.verify_reset_code(data)


@auth_router.post(
    "/reset-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reset Password Using Token",
)
async def reset_password(
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
):
    """تنظیم رمز عبور جدید با توکن بازنشانی"""
    return await service.reset_password(data)
