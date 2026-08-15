from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SettingUpdate, SettingResponse
from .service import SettingService
from core.database import get_db

# Import access control dependencies
from modules.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/settings", tags=["System Settings"])

@router.get(
    "/", 
    response_model=SettingResponse, 
    summary="Get all system settings"
)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)  # Only authenticated users
):
    """Retrieve current system settings (creates default settings if they do not exist)."""
    return await SettingService.get_or_create_settings(db)

@router.patch(
    "/", 
    response_model=SettingResponse, 
    summary="Update system settings"
)
async def update_system_settings(
    data: SettingUpdate, 
    db: AsyncSession = Depends(get_db),
    admin_user=Depends(require_admin)  # Exclusive access for Admin role only
):
    """Update specific fields of the system settings (e.g., alpha, beta, polling interval, token expiration, etc.)."""
    return await SettingService.update_settings(db, data)
