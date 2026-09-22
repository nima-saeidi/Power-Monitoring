from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# مدل‌های سیستم
from main_api.modules.devices.models import Feeder, Post, TimeseriesData
from main_api.modules.telemetry.schemas import TelemetryCreate, ActiveFeederConfig
from main_api.modules.settings.service import SettingService
from main_api.modules.settings.models import SystemSetting


class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _resolve_ip_and_port(feeder: Feeder) -> tuple[str, int]:
        """تعیین IP/Port نهایی فیدر: اولویت با مقدار خود فیدر، سپس Fallback به پست متصل."""
        ip = feeder.ip_address or (feeder.post.ip_address if feeder.post else None) or "127.0.0.1"
        port = feeder.port or (feeder.post.port if feeder.post else None) or 502
        return ip, port

    @staticmethod
    def _resolve_runtime_config(feeder: Feeder, system_settings: SystemSetting) -> dict:
        """
        تعیین مقادیر polling/modbus هر فیدر: پیش‌فرض از تنظیمات سراسری سیستم
        (system_settings) خوانده می‌شود؛ اگر خود فیدر در metadata_info مقدار
        اختصاصی داشته باشد، همان مقدار اختصاصی اولویت می‌گیرد.
        """
        config = {
            "scan_interval": system_settings.polling_interval,
            "max_failures": system_settings.max_telemetry_failures,
            "modbus_timeout": system_settings.modbus_timeout,
            "modbus_retry_count": system_settings.modbus_retry_count,
        }
        overrides = feeder.metadata_info if isinstance(feeder.metadata_info, dict) else {}
        for key in config:
            if key in overrides and overrides[key] is not None:
                config[key] = overrides[key]
        return config

    async def get_active_feeders(self) -> List[ActiveFeederConfig]:
        """
        واکشی لیست تمام فیدرهای فعال از دیتابیس به همراه پیکربندی polling/modbus
        که از تنظیمات سراسری سیستم (system_settings) اعمال می‌شود.
        """
        query = (
            select(Feeder)
            .options(selectinload(Feeder.post))
            .where(Feeder.is_active == True)
        )

        result = await self.session.execute(query)
        feeders = result.scalars().all()

        system_settings = await SettingService.get_or_create_settings(self.session)

        active_feeders_list: List[ActiveFeederConfig] = []

        for f in feeders:
            ip, port = self._resolve_ip_and_port(f)
            slave_id = f.modbus_address if f.modbus_address is not None else 1
            runtime_config = self._resolve_runtime_config(f, system_settings)

            active_feeders_list.append(
                ActiveFeederConfig(
                    feeder_id=f.id,
                    post_id=f.post_id,
                    name=f.name,
                    ip_address=ip,
                    port=port,
                    slave_id=slave_id,
                    is_active=f.is_active,
                    **runtime_config,
                )
            )

        return active_feeders_list

    async def create_record(self, data: TelemetryCreate) -> TimeseriesData:
        """
        ذخیره داده تله‌متری جدید در دیتابیس رابطه ای.
        """
        db_record = TimeseriesData(
            feeder_id=int(data.device_id) if str(data.device_id).isdigit() else 1,
            key="telemetry_packet",
            value=data.active_power,
            timestamp=func.now()
        )

        self.session.add(db_record)
        await self.session.commit()
        await self.session.refresh(db_record)

        return db_record
