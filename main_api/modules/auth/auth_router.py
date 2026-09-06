from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.database import get_db
from main_api.core.broker import get_rabbitmq_publisher, RabbitMQPublisher
from main_api.modules.auth.repository import UserRepository
from main_api.modules.auth.service import AuthService
from main_api.modules.auth.dependencies import get_current_user
from main_api.modules.auth.schemas import (
    AdminRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserProfileUpdate,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_rabbitmq_publisher),
) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo=repo, publisher=publisher)


@auth_router.post(
    "/register-admin",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register Initial Admin",
)
async def register_admin(
    data: AdminRegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    ثبت‌نام ادمین اولیه: اعتبارسنجی انجام شده و رویداد ایجاد به صف ارسال می‌شود.
    """
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
    """
    ورود کاربر و دریافت توکن دسترسی
    """
    return await service.login(data)


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Personal Profile",
)
async def get_my_profile(
    current_user=Depends(get_current_user),
):
    """
    دریافت اطلاعات پروفایل کاربر فعلی (عملیات خواندن مستقیم)
    """
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
    """
    به‌روزرسانی پروفایل کاربر فعلی: رویداد ویرایش به صف ارسال می‌شود.
    """
    return await service.update_profile(current_user.id, data)
