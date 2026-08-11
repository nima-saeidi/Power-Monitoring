from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from modules.auth.repository import UserRepository
from modules.auth.service import AuthService
from modules.auth.schemas import (
    AdminRegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    UserProfileUpdate,
    UserCreate,
    UserUpdate,
)
# New imports for RoleChecker
from modules.auth.dependencies import require_admin, get_current_user
from modules.auth.models import RoleEnum


router = APIRouter(prefix="/auth", tags=["User Management & Authentication"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)


@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register Initial Admin")
async def register_admin(data: AdminRegisterRequest, service: AuthService = Depends(get_auth_service)):
    return await service.register_admin(data)


@router.post("/login", response_model=TokenResponse, summary="Login and Get Token")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    return await auth_service.login(data, db=db)


# ==========================================
# User Management Routes
# ==========================================

@router.get("/users", response_model=list[UserResponse], summary="List All Users (Any Logged-in User)")
async def get_all_users(
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(get_current_user)  # 👈 Any logged-in user
):
    return await service.get_all_users()


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get Single User Info (Any Logged-in User)")
async def get_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(get_current_user)  # 👈 Any logged-in user
):
    return await service.get_user_by_id(user_id)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create User (Admin Only)")
async def create_user(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 Admin only
):
    return await service.create_user(data)


@router.put("/users/{user_id}", response_model=UserResponse, summary="Update User (Admin Only)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 Admin only
):
    return await service.update_user(user_id, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK, summary="Delete User (Admin Only)")
async def delete_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 Admin only
):
    return await service.delete_user(user_id)


# ==========================================
# User Profile Management Routes
# ==========================================

@router.get("/me", response_model=UserResponse, summary="Get Personal Profile")
async def get_my_profile(current_user = Depends(get_current_user)):
    """
    Retrieve the profile info of the currently logged-in user.
    """
    return current_user


@router.put("/me", response_model=UserResponse, summary="Update Personal Profile")
async def update_my_profile(
    data: UserProfileUpdate,
    current_user = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service)
):
    """
    Update the logged-in user's own profile info (e.g. name and national ID).
    """
    return await service.update_profile(current_user.id, data)


@router.get("/roles", summary="List All Available Roles")
async def get_roles():
    """
    Returns the list of roles defined in the system for use in the frontend
    (e.g. in the user create/edit forms). No token required for easy access in forms.
    """
    roles = [
        {"value": RoleEnum.ADMIN.value, "label": "System Admin"},
        {"value": RoleEnum.TECHNICAL_OPERATOR.value, "label": "Technical Operator"},
        {"value": RoleEnum.USER.value, "label": "Regular User"},
    ]
    return {"roles": roles}
