from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SettingUpdate, SettingResponse
from .service import SettingService
from main_api.core.database import get_db

# Import access control dependencies
from main_api.modules.auth.dependencies import get_current_user, require_admin

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
    """
    Retrieve current system settings.
    If settings do not exist, creates and returns default settings including:
    alfa, beta, token expiration, polling interval, max telemetry failures,
    session timeout, max login attempts, and data retention days.
    """
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
    """
    Update specific fields of the system settings.

    Allowed fields for update:
    - alfa
    - beta
    - access_token_expire_minutes
    - session_timeout_minutes
    - polling_interval
    - max_telemetry_failures
    - max_login_attempts
    - data_retention_days
    """
    return await SettingService.update_settings(db, data)
