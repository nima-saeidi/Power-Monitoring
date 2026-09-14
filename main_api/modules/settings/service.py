# main_api/modules/settings/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import SettingRepository
from .models import SystemSetting
from .schemas import SettingUpdate, SettingResponse
from main_api.core.broker import RabbitMQPublisher

# متغیر سراسری (Global) برای کش کردن تنظیمات در RAM
_settings_cache: SystemSetting | None = None


class SettingService:
    @staticmethod
    async def get_or_create_settings(db: AsyncSession, bypass_cache: bool = False) -> SystemSetting:
        """
        دریافت تنظیمات سیستم. ابتدا از کش خوانده می‌شود.
        در صورت عدم وجود در دیتابیس، مقادیر پیش‌فرض ساخته و بازگردانده می‌شوند.
        """
        global _settings_cache

        # ۱. اگر کش موجود است و bypass نشده، همان را سریع برگردان
        if _settings_cache is not None and not bypass_cache:
            return _settings_cache

        # ۲. در غیر این صورت به دیتابیس مراجعه کن
        settings = await SettingRepository.get_settings(db)
        if not settings:
            settings = await SettingRepository.create_default_settings(db)

        # ۳. کش را برای درخواست‌های بعدی آپدیت کن
        _settings_cache = settings
        return settings

    @staticmethod
    async def update_settings(
            db: AsyncSession,
            data: SettingUpdate,
            publisher: RabbitMQPublisher
    ) -> SystemSetting:
        """
        بروزرسانی تنظیمات سیستم، اعمال فوری در کش و انتشار رویداد در صف.
        """
        global _settings_cache

        # برای اطمینان از اینکه جدیدترین نسخه دیتابیس را آپدیت می‌کنیم، کش را بای‌پس می‌کنیم
        settings = await SettingService.get_or_create_settings(db, bypass_cache=True)

        # استخراج فیلدهای ارسال شده در بدنه درخواست (بدون مقادیر Null/Unset)
        update_data = data.model_dump(exclude_unset=True)

        # اعمال تغییرات در دیتابیس
        updated_settings = await SettingRepository.update_settings(db=db, settings=settings, update_data=update_data)

        # بروزرسانی بلادرنگ سیستم با جایگزین کردن کش
        _settings_cache = updated_settings

        # ---------------------------------------------------------
        # ارسال رویداد آپدیت تنظیمات به RabbitMQ برای سایر سرویس‌ها
        # ---------------------------------------------------------
        # تبدیل مدل دیتابیس به دیکشنری تمیز با استفاده از Pydantic
        settings_dict = SettingResponse.model_validate(updated_settings).model_dump(mode="json")

        await publisher.publish_event(
            routing_key="settings.updated",
            message={
                "event": "SETTINGS_UPDATED",
                "data": settings_dict
            }
        )

        return updated_settings
