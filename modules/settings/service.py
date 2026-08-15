from sqlalchemy.ext.asyncio import AsyncSession
from .repository import SettingRepository
from .models import SystemSetting
from .schemas import SettingUpdate

class SettingService:
    @staticmethod
    async def get_or_create_settings(db: AsyncSession) -> SystemSetting:
        settings = await SettingRepository.get_settings(db)
        if not settings:
            settings = await SettingRepository.create_default_settings(db)
        return settings

    @staticmethod
    async def update_settings(db: AsyncSession, data: SettingUpdate) -> SystemSetting:
        settings = await SettingService.get_or_create_settings(db)
        # فقط فیلدهایی که در بادی درخواست فرستاده شده‌اند را استخراج می‌کنیم
        update_data = data.model_dump(exclude_unset=True)
        return await SettingRepository.update_settings(db=db, settings=settings, update_data=update_data)
