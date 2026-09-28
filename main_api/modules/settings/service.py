from main_api.core.tasks import fire_and_forget
from typing import Optional
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import SettingRepository
from .models import SystemSetting
from .schemas import SettingUpdate, SettingResponse

from main_api.core.broker import RabbitMQPublisher

from main_api.modules.audit_logs.services import send_audit_log

_settings_cache: SystemSetting | None = None


class SettingService:
    @staticmethod
    async def get_or_create_settings(db: AsyncSession, bypass_cache: bool = False) -> SystemSetting:
        global _settings_cache

        if _settings_cache is not None and not bypass_cache:
            return _settings_cache

        settings = await SettingRepository.get_settings(db)
        if not settings:
            settings = await SettingRepository.create_default_settings(db)

            fire_and_forget(send_audit_log(
                action="INITIALIZE_SYSTEM_SETTINGS",
                username="System",
                success=True,
                severity="INFO",
                description="تنظیمات پیش‌فرض سیستم برای اولین بار مقداردهی و در دیتابیس ایجاد شد."
            ))

        _settings_cache = settings
        return settings

    @staticmethod
    async def update_settings(
            db: AsyncSession,
            data: SettingUpdate,
            broker: RabbitMQPublisher,
            background_tasks: Optional[BackgroundTasks] = None,
            username: Optional[str] = "System"
    ) -> SystemSetting:
        global _settings_cache

        settings = await SettingService.get_or_create_settings(db, bypass_cache=True)

        update_data = data.model_dump(exclude_unset=True)

        updated_settings = await SettingRepository.update_settings(db=db, settings=settings, update_data=update_data)

        _settings_cache = updated_settings
        from main_api.modules.telemetry.live import live_monitor
        live_monitor.invalidate()

        if update_data:
            changed_fields = ", ".join(update_data.keys())
            log_coroutine = send_audit_log(
                action="UPDATE_SYSTEM_SETTINGS",
                username=username,
                success=True,
                severity="WARNING",
                description=f"تنظیمات سیستم ویرایش شد. فیلدهای تغییر یافته: {changed_fields}"
            )
            if background_tasks:
                background_tasks.add_task(lambda: fire_and_forget(log_coroutine))
            else:
                fire_and_forget(log_coroutine)

        settings_dict = SettingResponse.model_validate(updated_settings).model_dump(mode="json")

        await broker.publish_event(
            routing_key="settings.updated",
            message={
                "event": "SETTINGS_UPDATED",
                "data": settings_dict
            }
        )

        return updated_settings
