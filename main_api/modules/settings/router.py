# main_api/modules/settings/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SettingUpdate, SettingResponse
from .service import SettingService
from main_api.core.database import get_db
from main_api.core.rabbitmq import get_rabbitmq_publisher, RabbitMQPublisher

# Import access control dependencies
from main_api.modules.auth.dependencies import require_any_user, require_admin

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get(
    "/",
    response_model=SettingResponse,
    summary="Get all system settings"
)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_user)  # Only authenticated users with valid roles
):
    return await SettingService.get_or_create_settings(db)


@router.put("/", response_model=SettingResponse)
async def update_system_settings(
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    broker: MessageBroker = Depends(get_message_broker) # اضافه شدن تزریق وابستگی
):
    return await SettingService.update_settings(db=db, data=data, broker=broker)
