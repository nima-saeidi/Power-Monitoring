from sqlalchemy.ext.asyncio import AsyncSession
from .repository import SettingRepository
from .models import SystemSetting
from .schemas import SettingUpdate


class SettingService:
    @staticmethod
    async def get_or_create_settings(db: AsyncSession) -> SystemSetting:
        """
        دریافت تنظیمات سیستم. در صورت عدم وجود، مقادیر پیش‌فرض (شامل فیلدهای جدید)
        ساخته و بازگردانده می‌شوند.
        """
        settings = await SettingRepository.get_settings(db)
        if not settings:
            settings = await SettingRepository.create_default_settings(db)
        return settings

    @staticmethod
    async def update_settings(db: AsyncSession, data: SettingUpdate) -> SystemSetting:
        """
        بروزرسانی تنظیمات سیستم.
        فقط فیلدهایی که ارسال شده‌اند آپدیت می‌شوند.
        """
        settings = await SettingService.get_or_create_settings(db)

        # استخراج فیلدهای ارسال شده در بدنه درخواست (شامل فیلدهای جدید در صورت وجود)
        update_data = data.model_dump(exclude_unset=True)

        return await SettingRepository.update_settings(db=db, settings=settings, update_data=update_data)
