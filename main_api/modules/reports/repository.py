# app/reports/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime
from typing import List

# Post از devices و TimeseriesData از telemetry خوانده می‌شود
from main_api.modules.devices.models import Post
from main_api.modules.telemetry.models import TimeseriesData


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ۱. دریافت تاریخچه فیدر
    async def get_feeder_history(self, feeder_id: int, start_date: datetime, end_date: datetime) -> List[
        TimeseriesData]:
        stmt = select(TimeseriesData).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        ).order_by(TimeseriesData.timestamp.asc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ۲. دریافت گزارش آماری (میانگین، حداکثر و حداقل) برای نمودارها
    async def get_aggregated_stats(self, feeder_id: int, parameter_key: str, start_date: datetime, end_date: datetime):
        stmt = select(
            func.avg(TimeseriesData.value_int).label('avg_value'),
            func.max(TimeseriesData.value_int).label('max_value'),
            func.min(TimeseriesData.value_int).label('min_value')
        ).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.key == parameter_key,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        )

        result = await self.db.execute(stmt)
        return result.first()

    # ۳. دریافت وضعیت فعلی تمامی پست‌ها برای داشبورد
    async def get_all_posts_status(self) -> List[Post]:
        stmt = select(Post)
        result = await self.db.execute(stmt)
        return result.scalars().all()
