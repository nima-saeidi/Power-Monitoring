from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SettingUpdate, SettingResponse
from .service import SettingService
from core.database import get_db

# وارد کردن وابستگی‌های کنترل دسترسی
from modules.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/settings", tags=["System Settings"])

@router.get(
    "/", 
    response_model=SettingResponse, 
    summary="دریافت کلیه تنظیمات سیستم"
)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)  # فقط کاربران لاگین شده
):
    """دریافت تنظیمات فعلی سیستم (در صورت نبود، با مقادیر پیش‌فرض ایجاد می‌شود)."""
    return await SettingService.get_or_create_settings(db)

@router.patch(
    "/", 
    response_model=SettingResponse, 
    summary="به‌روزرسانی تنظیمات سیستم"
)
async def update_system_settings(
    data: SettingUpdate, 
    db: AsyncSession = Depends(get_db),
    admin_user=Depends(require_admin)  # دسترسی انحصاری فقط برای نقش Admin
):
    """به‌روزرسانی هر یک از فیلدهای تنظیمات (آلفا، بتا، بازه پولینگ، انقضای توکن و...)."""
    return await SettingService.update_settings(db, data)
