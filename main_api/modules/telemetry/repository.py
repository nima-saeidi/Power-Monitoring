from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.modules.feeders.models import Feeder, TimeseriesData
from main_api.modules.telemetry.schemas import TelemetryCreate, ActiveFeederConfig
from main_api.modules.settings.service import SettingService
from main_api.modules.settings.models import SystemSetting


def overrides_of(feeder: Feeder) -> dict:
    return feeder.metadata_info if isinstance(feeder.metadata_info, dict) else {}


class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _resolve_ip_and_port(feeder: Feeder) -> tuple[str, int]:
        ip = feeder.ip_address or (feeder.post.ip_address if feeder.post else None) or "127.0.0.1"
        port = feeder.port or (feeder.post.port if feeder.post else None) or 502
        return ip, port

    @staticmethod
    def _resolve_runtime_config(feeder: Feeder, system_settings: SystemSetting) -> dict:
        config = {
            "scan_interval": system_settings.polling_interval,
            "max_failures": system_settings.max_telemetry_failures,
            "modbus_timeout": system_settings.modbus_timeout,
            "modbus_retry_count": system_settings.modbus_retry_count,
            "offline_retry_interval": system_settings.feeder_offline_retry_interval,
        }
        overrides = feeder.metadata_info if isinstance(feeder.metadata_info, dict) else {}
        for key in config:
            if key in overrides and overrides[key] is not None:
                config[key] = overrides[key]
        return config

    async def get_active_feeders(self) -> List[ActiveFeederConfig]:
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
                    is_online=f.is_online,
                    active_power_register=f.active_power_register,
                    reactive_power_register=f.reactive_power_register,
                    voltage_register=f.voltage_register,
                    current_register=f.current_register,
                    power_factor_register=f.power_factor_register,
                    register_scales=overrides_of(f).get("register_scales") or {},
                    signed_registers=overrides_of(f).get("signed_registers") or [],
                    **runtime_config,
                )
            )

        return active_feeders_list

    async def update_feeder_status(
            self,
            feeder_id: int,
            is_online: bool,
            consecutive_failures: int,
            last_success: Optional[datetime] = None,
    ) -> Optional[Feeder]:
        result = await self.session.execute(select(Feeder).where(Feeder.id == feeder_id))
        feeder = result.scalar_one_or_none()
        if not feeder:
            return None

        feeder.is_online = is_online
        feeder.consecutive_failures = consecutive_failures
        if last_success is not None:
            feeder.last_success = last_success

        await self.session.commit()
        await self.session.refresh(feeder)
        return feeder

    async def create_record(self, data: TelemetryCreate) -> TimeseriesData:
        raw_id = getattr(data, "feeder_id", getattr(data, "device_id", None))
        try:
            target_feeder_id = int(raw_id) if raw_id is not None else 1
        except (ValueError, TypeError):
            target_feeder_id = 1

        ts = getattr(data, "timestamp", None)
        if ts is None:
            ts = func.now()

        db_record = TimeseriesData(
            feeder_id=target_feeder_id,
            key="telemetry_packet",
            value=getattr(data, "active_power", 0.0),
            timestamp=ts
        )

        self.session.add(db_record)
        await self.session.commit()
        await self.session.refresh(db_record)

        return db_record
