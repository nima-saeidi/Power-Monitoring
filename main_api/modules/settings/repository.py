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
        # مقادیر پیش‌فرض جدید به همراه فیلدهای قبلی اضافه شدند
        settings = SystemSetting(
            critical_threshold=0.7,
            warning_threshold=0.4,
            access_token_expire_minutes=1440,
            session_timeout_minutes=30,      # پیش‌فرض: 30 دقیقه
            polling_interval=5,
            max_telemetry_failures=3,
            max_login_attempts=5,            # پیش‌فرض: 5 تلاش ناموفق
            data_retention_days=90           # پیش‌فرض: 90 روز نگهداری لاگ‌ها و داده‌ها
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
