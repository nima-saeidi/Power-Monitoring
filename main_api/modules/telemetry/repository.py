from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# مدل‌های سیستم
from main_api.modules.devices.models import Feeder, Post, TimeseriesData
from main_api.modules.telemetry.schemas import TelemetryCreate, ActiveFeederConfig


class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_feeders(self) -> List[ActiveFeederConfig]:
        """
        واکشی لیست تمام فیدرهای فعال از دیتابیس.
        در صورتی که IP یا Port فیدر خالی باشد، به صورت Fallback از مشخصات Post متصل استفاده می‌شود.
        """
        query = (
            select(Feeder)
            .options(selectinload(Feeder.post))
            .where(Feeder.is_active == True)
        )

        result = await self.session.execute(query)
        feeders = result.scalars().all()

        active_feeders_list: List[ActiveFeederConfig] = []

        for f in feeders:
            # تعیین IP: اولویت با IP فیدر، در صورت نبود از IP پست متناظر استفاده می‌شود
            ip = f.ip_address or (f.post.ip_address if f.post else None) or "127.0.0.1"

            # تعیین پورت: اولویت با پورت فیدر، سپس پورت پست، در نهایت پیش‌فرض 502
            port = f.port or (f.post.port if f.post else None) or 502

            # تعیین Modbus Unit ID (Slave ID)
            slave_id = f.modbus_address if f.modbus_address is not None else 1

            # استخراج فاصله زمانی اسکن (scan_interval) در صورت وجود در metadata_info
            scan_interval = 5
            if f.metadata_info and isinstance(f.metadata_info, dict):
                scan_interval = f.metadata_info.get("scan_interval", 5)

            active_feeders_list.append(
                ActiveFeederConfig(
                    feeder_id=f.id,
                    post_id=f.post_id,
                    name=f.name,
                    ip_address=ip,
                    port=port,
                    slave_id=slave_id,
                    scan_interval=scan_interval,
                    is_active=f.is_active
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
