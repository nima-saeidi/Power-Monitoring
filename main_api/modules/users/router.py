from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from main_api.core.database import get_db
from main_api.core.rate_limit import (
    limiter, CHANGE_PASSWORD_LIMIT, FORGOT_PASSWORD_LIMIT, RESET_PASSWORD_LIMIT, VERIFY_CODE_LIMIT
)
from main_api.core.broker import get_rabbitmq_publisher, RabbitMQPublisher
from main_api.modules.users.repository import UserRepository
from main_api.modules.users.service import UserService
from main_api.modules.auth.service import AuthService
from main_api.modules.auth.dependencies import (
    require_admin,
    require_any_user,
    require_tech_or_admin
)
from main_api.core.domain import PAGES
from main_api.modules.users.models import RoleEnum
from main_api.modules.users.schemas import (
    UserResponse,
    UserCreate,
    UserUpdate,
)
from main_api.modules.auth.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, VerifyCodeRequest, ForgotPasswordResponse,
    VerifyCodeResponse
)

user_router = APIRouter(prefix="/users", tags=["User Management"])

def get_user_service(
    db: AsyncSession = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_rabbitmq_publisher),
) -> UserService:
    repo = UserRepository(db)
    return UserService(repository=repo, publisher=publisher, db=db)

def get_auth_service(
    db: AsyncSession = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_rabbitmq_publisher),
) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repository=repo, publisher=publisher, db=db)


@user_router.get("", response_model=list[UserResponse], summary="List All Users (Admin / Technical Operator)")
async def get_all_users(
    service: UserService = Depends(get_user_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.get_all_users()

@user_router.post("/change-password", status_code=status.HTTP_200_OK, summary="Change Password (Current Authenticated User)")
@limiter.limit(CHANGE_PASSWORD_LIMIT)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(require_any_user)
):
    return await service.change_password(user_id=current_user.id, data=data)

@user_router.get("/{user_id}", response_model=UserResponse, summary="Get Single User Info (Admin / Operator / Self)")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user = Depends(require_any_user)
):
    if current_user.role == RoleEnum.USER and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="شما مجوز لازم برای انجام این عملیات را ندارید.")
    return await service.get_user_by_id(user_id)

@user_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create User (Admin Only)")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
    current_admin = Depends(require_admin)
):
    return await service.create_user(data, current_user=current_admin)

@user_router.put("/{user_id}", response_model=UserResponse, summary="Update User (Admin Only)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_admin = Depends(require_admin)
):
    return await service.update_user(user_id, data, current_user=current_admin)

@user_router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Delete User (Admin Only)")
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_admin = Depends(require_admin)
):
    return await service.delete_user(user_id, current_user=current_admin)

@user_router.get("/pages/list", summary="List panel pages that can be granted to an account")
async def get_pages(current_user=Depends(require_any_user)):
    return {"pages": [{"value": key, "label": label} for key, label in PAGES.items()]}


@user_router.get("/roles/list", summary="List All Available Roles (All Users)")
async def get_roles(
    current_user = Depends(require_any_user)
):
    roles = [
        {"value": RoleEnum.ADMIN.value, "label": "System Admin"},
        {"value": RoleEnum.TECHNICAL_OPERATOR.value, "label": "Technical Operator"},
        {"value": RoleEnum.USER.value, "label": "Regular User"},
    ]
    return {"roles": roles}


@user_router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK, summary="Request OTP Code")
@limiter.limit(FORGOT_PASSWORD_LIMIT)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service)
):
    return await service.forgot_password(data, background_tasks)

@user_router.post("/verify-code", response_model=VerifyCodeResponse, status_code=status.HTTP_200_OK, summary="Verify OTP Code")
@limiter.limit(VERIFY_CODE_LIMIT)
async def verify_code(
    request: Request,
    data: VerifyCodeRequest,
    service: AuthService = Depends(get_auth_service)
):
    return await service.verify_reset_code(data)

@user_router.post("/reset-password", status_code=status.HTTP_200_OK, summary="Set New Password")
@limiter.limit(RESET_PASSWORD_LIMIT)
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service)
):
    return await service.reset_password(data)
