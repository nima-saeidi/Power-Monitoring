from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from modules.auth.repository import UserRepository
from modules.auth.service import AuthService
from modules.auth.schemas import AdminRegisterRequest, LoginRequest, UserResponse, TokenResponse
# این ایمپورت را اضافه کنید
from modules.auth.dependencies import get_admin_user, get_tech_or_admin_user
from modules.auth.schemas import UserCreate, UserUpdate

router = APIRouter(prefix="/auth", tags=["مدیریت کاربران و احراز هویت"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)

# 1. این مسیر باز می‌ماند تا بتوانید ادمین اولیه را در دیتابیس خالی بسازید
@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="ثبت‌نام ادمین اولیه")
async def register_admin(data: AdminRegisterRequest, service: AuthService = Depends(get_auth_service)):
    return await service.register_admin(data)

# 2. مسیر ورود (نیاز به دسترسی خاصی ندارد)
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    return await auth_service.login(data, db=db) # ارسال db


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد کاربر جدید (فقط ادمین)")
async def create_user(
    data: UserCreate, 
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(get_admin_user)
):
    return await service.create_user(data)

# دریافت لیست تمام کاربران
@router.get("/users", response_model=list[UserResponse], summary="لیست تمام کاربران (فقط ادمین)")
async def get_all_users(
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(get_admin_user)
):
    return await service.get_all_users()

# دریافت یک کاربر خاص
@router.get("/users/{user_id}", response_model=UserResponse, summary="دریافت اطلاعات یک کاربر (فقط ادمین)")
async def get_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(get_admin_user)
):
    return await service.get_user_by_id(user_id)

# ویرایش اطلاعات یا نقش یک کاربر
@router.put("/users/{user_id}", response_model=UserResponse, summary="ویرایش کاربر (فقط ادمین)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(get_admin_user)
):
    return await service.update_user(user_id, data)

# حذف کاربر
@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK, summary="حذف کاربر (فقط ادمین)")
async def delete_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(get_admin_user)
):
    return await service.delete_user(user_id)