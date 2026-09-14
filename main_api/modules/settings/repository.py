# main_api/modules/settings/repository.py
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import SystemSetting


class SettingRepository:
    @staticmethod
    async def get_settings(db: AsyncSession) -> SystemSetting | None:
        result = await db.execute(select(SystemSetting))
        return result.scalars().first()

    @staticmethod
    async def create_default_settings(db: AsyncSession) -> SystemSetting:
        # مقادیر پیش‌فرض دقیقاً منطبق بر مدل تنظیم شده‌اند
        settings = SystemSetting(
            critical_threshold=90.0,
            warning_threshold=75.0,
            access_token_expire_minutes=1440,
            max_login_attempts=5,
            lockout_duration_minutes=30,
            session_timeout_minutes=120,
            polling_interval=5,
            max_telemetry_failures=3,
            modbus_timeout=3,
            modbus_retry_count=3,
            notification_retry_attempts=3,
            notification_cooldown_seconds=300,
            report_generation_timeout=300,
            max_export_records=10000
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def update_settings(db: AsyncSession, settings: SystemSetting, update_data: Dict[str, Any]) -> SystemSetting:
        for key, value in update_data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        await db.commit()
        await db.refresh(settings)
        return settings
