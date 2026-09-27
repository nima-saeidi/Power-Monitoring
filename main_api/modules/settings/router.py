from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SettingUpdate, SettingResponse
from .service import SettingService
from main_api.core.database import get_db
from main_api.core.rabbitmq import get_rabbitmq_publisher, RabbitMQPublisher

from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin
from main_api.modules.users.models import RoleEnum

router = APIRouter(prefix="/settings", tags=["System Settings"])

ADMIN_ONLY_FIELDS = {
    "access_token_expire_minutes",
    "max_login_attempts",
    "lockout_duration_minutes",
    "session_timeout_minutes",
}


@router.get(
    "/",
    response_model=SettingResponse,
    summary="Get all system settings"
)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_user)
):
    return await SettingService.get_or_create_settings(db)


@router.put("/", response_model=SettingResponse, summary="Update system settings")
async def update_system_settings(
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_rabbitmq_publisher),
    current_user=Depends(require_tech_or_admin)
):
    restricted = ADMIN_ONLY_FIELDS & data.model_dump(exclude_unset=True).keys()
    if restricted and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"تغییر تنظیمات امنیتی فقط توسط ادمین مجاز است: {', '.join(sorted(restricted))}"
        )
    return await SettingService.update_settings(
        db=db, data=data, broker=broker, username=current_user.email
    )
