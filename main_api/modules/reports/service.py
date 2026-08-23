# app/reports/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import ReportRepository


class ReportService:
    def __init__(self, db: AsyncSession):
        self.repo = ReportRepository(db)

    async def fetch_feeder_report(self, feeder_id: int, start_date, end_date):
        # فراخوانی متد به صورت async
        return await self.repo.get_feeder_history(feeder_id, start_date, end_date)

    async def fetch_aggregated_report(self, feeder_id: int, parameter_key: str, start_date, end_date):
        row = await self.repo.get_aggregated_stats(feeder_id, parameter_key, start_date, end_date)

        return {
            "feeder_id": feeder_id,
            "parameter": parameter_key,
            "avg_value": row.avg_value if row else None,
            "max_value": row.max_value if row else None,
            "min_value": row.min_value if row else None,
            "start_date": start_date,
            "end_date": end_date
        }

    async def fetch_posts_status(self):
        return await self.repo.get_all_posts_status()
