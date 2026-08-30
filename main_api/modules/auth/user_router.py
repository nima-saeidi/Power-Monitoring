from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from main_api.core.database import get_db
from main_api.modules.auth.repository import UserRepository
from main_api.modules.auth.service import AuthService
from main_api.modules.auth.dependencies import (
    require_admin,
    require_any_user
)
from main_api.modules.auth.models import RoleEnum
from main_api.modules.auth.schemas import (
    UserResponse,
    UserCreate,
    UserUpdate,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
)

user_router = APIRouter(prefix="/users", tags=["User Management"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

# ==========================================
# User Management Routes
# ==========================================

@user_router.get("", response_model=list[UserResponse], summary="List All Users (All Users)")
async def get_all_users(
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(require_any_user)  # ادمین، اپراتور فنی و کاربر عادی
):
    return await service.get_all_users()

@user_router.post("/change-password", status_code=status.HTTP_200_OK, summary="Change Password (Current Authenticated User)")
async def change_password(
    data: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(require_any_user)  # کاربر یا ادمین واردشده
):
    """
    تغییر رمز عبور کاربر/ادمین جاری با دریافت رمز قبلی و رمز جدید
    """
    return await service.change_password(user_id=current_user.id, data=data)

@user_router.get("/{user_id}", response_model=UserResponse, summary="Get Single User Info (All Users)")
async def get_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(require_any_user)  # ادمین، اپراتور فنی و کاربر عادی
):
    return await service.get_user_by_id(user_id)

@user_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create User (Admin Only)")
async def create_user(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # فقط ادمین
):
    return await service.create_user(data)

@user_router.put("/{user_id}", response_model=UserResponse, summary="Update User (Admin Only)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # فقط ادمین
):
    return await service.update_user(user_id, data)

@user_router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Delete User (Admin Only)")
async def delete_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # فقط ادمین
):
    return await service.delete_user(user_id)

@user_router.get("/roles/list", summary="List All Available Roles (All Users)")
async def get_roles(
    current_user = Depends(require_any_user) # ادمین، اپراتور فنی و کاربر عادی
):
    """
    Returns the list of roles defined in the system for use in the frontend
    (e.g. in the user create/edit forms).
    """
    roles = [
        {"value": RoleEnum.ADMIN.value, "label": "System Admin"},
        {"value": RoleEnum.TECHNICAL_OPERATOR.value, "label": "Technical Operator"},
        {"value": RoleEnum.USER.value, "label": "Regular User"},
    ]
    return {"roles": roles}


@user_router.post("/forgot-password", status_code=status.HTTP_200_OK, summary="Request Password Reset")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service)
):
    """
    دریافت ایمیل و ارسال لینک حاوی توکن به صورت Background Task
    """
    return await service.forgot_password(data, background_tasks)


@user_router.post("/reset-password", status_code=status.HTTP_200_OK, summary="Reset Password using Token")
async def reset_password(
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    تغییر رمز عبور در صورت معتبر بودن توکن (ارسال شده از سمت فرانت‌اند)
    """
    return await service.reset_password(data)