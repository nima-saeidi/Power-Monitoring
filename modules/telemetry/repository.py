from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from modules.telemetry.models import TimeseriesData
from modules.telemetry.schemas import TelemetryCreate

class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_record(self, data: TelemetryCreate) -> TimeseriesData:
        new_record = TimeseriesData(
            post_id=data.post_id,
            parameter_name=data.parameter_name,
            value_int=data.value_int,
            value_float=data.value_float,
            value_str=data.value_str,
            value_bool=data.value_bool
        )
        self.session.add(new_record)
        await self.session.flush()
        await self.session.refresh(new_record)
        return new_record

    async def get_history(self, post_id: int, limit: int = 100):
        stmt = select(TimeseriesData).where(TimeseriesData.post_id == post_id).order_by(TimeseriesData.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
