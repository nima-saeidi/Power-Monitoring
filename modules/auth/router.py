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
    UserUpdate
)
# ایمپورت‌های جدید بر اساس RoleChecker
from modules.auth.dependencies import require_admin, get_current_user
from modules.auth.models import RoleEnum 


router = APIRouter(prefix="/auth", tags=["مدیریت کاربران و احراز هویت"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)
    return AuthService(repo)


@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="ثبت‌نام ادمین اولیه")
async def register_admin(data: AdminRegisterRequest, service: AuthService = Depends(get_auth_service)):
    return await service.register_admin(data)


@router.post("/login", response_model=TokenResponse, summary="ورود به سیستم و دریافت توکن")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(UserRepository(db))
    return await auth_service.login(data, db=db)


# ==========================================
# مسیرهای مدیریت کاربران
# ==========================================

@router.get("/users", response_model=list[UserResponse], summary="لیست تمام کاربران (دسترسی برای همه)")
async def get_all_users(
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(get_current_user)  # 👈 دسترسی برای همه کاربران لاگین‌شده
):
    return await service.get_all_users()


@router.get("/users/{user_id}", response_model=UserResponse, summary="دریافت اطلاعات یک کاربر (دسترسی برای همه)")
async def get_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_user = Depends(get_current_user)  # 👈 دسترسی برای همه کاربران لاگین‌شده
):
    return await service.get_user_by_id(user_id)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد کاربر جدید (فقط ادمین)")
async def create_user(
    data: UserCreate, 
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 فقط ادمین
):
    return await service.create_user(data)


@router.put("/users/{user_id}", response_model=UserResponse, summary="ویرایش کاربر (فقط ادمین)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 فقط ادمین
):
    return await service.update_user(user_id, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK, summary="حذف کاربر (فقط ادمین)")
async def delete_user(
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    current_admin = Depends(require_admin)  # 👈 فقط ادمین
):
    return await service.delete_user(user_id)


# ==========================================
# مسیرهای مدیریت پروفایل کاربری (Profile)
# ==========================================

@router.get("/me", response_model=UserResponse, summary="دریافت اطلاعات پروفایل شخصی")
async def get_my_profile(current_user = Depends(get_current_user)):
    """
    دریافت اطلاعات کاربری شخصی که لاگین کرده است.
    """
    return current_user


@router.put("/me", response_model=UserResponse, summary="ویرایش پروفایل شخصی")
async def update_my_profile(
    data: UserProfileUpdate,
    current_user = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service)
):
    """
    بروزرسانی اطلاعات پروفایل شخصی (مانند نام و کد ملی) توسط خود کاربر.
    """
    return await service.update_profile(current_user.id, data)


@router.get("/roles", summary="دریافت لیست نقش‌های موجود در سیستم")
async def get_roles():
    """
    این API لیست نقش‌های تعریف شده در سیستم را برای استفاده در فرانت‌اند (مثل فرم ایجاد/ویرایش کاربر) برمی‌گرداند.
    بدون نیاز به توکن برای دسترسی آسان در فرم‌ها.
    """
    roles = [
        {"value": RoleEnum.ADMIN.value, "label": "مدیر سیستم"},
        {"value": RoleEnum.TECHNICAL_OPERATOR.value, "label": "اپراتور فنی"},
        {"value": RoleEnum.USER.value, "label": "کاربر عادی"}
    ]
    return {"roles": roles}
