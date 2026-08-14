from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from main_api.core.database import get_db
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

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

@auth_router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register Initial Admin")
async def register_admin(data: AdminRegisterRequest, service: AuthService = Depends(get_auth_service)):
    return await service.register_admin(data)

@auth_router.post("/login", response_model=TokenResponse, summary="Login and Get Token")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    return await auth_service.login(data, db=db)



@auth_router.get("/me", response_model=UserResponse, summary="Get Personal Profile")
async def get_my_profile(current_user = Depends(get_current_user)):
    return current_user

@auth_router.put("/me", response_model=UserResponse, summary="Update Personal Profile")
async def update_my_profile(
    data: UserProfileUpdate,
    current_user = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service)
):
    return await service.update_profile(current_user.id, data)
