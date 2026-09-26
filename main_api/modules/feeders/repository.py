from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.modules.feeders.models import Feeder
from main_api.modules.feeders.schemas import FeederCreate, FeederUpdate


class FeederRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feeder(self, data: FeederCreate) -> Feeder:
        feeder = Feeder(**data.model_dump())
        self.db.add(feeder)
        await self.db.commit()
        await self.db.refresh(feeder)
        return feeder

    async def get_all_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100,
                              feeder_type: Optional[str] = None, is_active: Optional[bool] = None,
                              is_online: Optional[bool] = None, load_status: Optional[str] = None,
                              search: Optional[str] = None) -> List[Feeder]:
        query = select(Feeder).options(
            selectinload(Feeder.post)
        )
        if post_id:
            query = query.where(Feeder.post_id == post_id)
        if feeder_type:
            query = query.where(Feeder.feeder_type == feeder_type)
        if is_active is not None:
            query = query.where(Feeder.is_active == is_active)
        if is_online is not None:
            query = query.where(Feeder.is_online == is_online)
        if load_status:
            query = query.where(Feeder.load_status == load_status)
        if search:
            query = query.where(Feeder.name.ilike(f"%{search}%"))
        query = query.order_by(Feeder.id).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_feeder_by_id(self, feeder_id: int) -> Optional[Feeder]:
        query = select(Feeder).options(
            selectinload(Feeder.post)
        ).where(Feeder.id == feeder_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_feeder(self, feeder: Feeder, data: FeederUpdate) -> Feeder:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(feeder, key, value)
        await self.db.commit()
        await self.db.refresh(feeder)
        return feeder

    async def delete_feeder(self, feeder: Feeder) -> None:
        await self.db.delete(feeder)
        await self.db.commit()
