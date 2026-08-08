from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

# مدل‌ها و اسکیماها شامل Link اضافه شدند
from modules.devices.models import Post, Feeder, Location, Link
from modules.devices.schemas import (
    PostCreate, PostUpdate,
    FeederCreate, FeederUpdate,
    LocationCreate, LocationUpdate,
    LinkCreate, LinkUpdate
)


class DeviceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ================= Location CRUD =================
    async def create_location(self, data: LocationCreate) -> Location:
        location = Location(**data.model_dump())
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return await self.get_location_by_id(location.id)

    async def get_all_locations(self, skip: int = 0, limit: int = 100) -> List[Location]:
        query = select(Location).options(
            selectinload(Location.children),
            selectinload(Location.posts)
        ).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_root_locations(self) -> List[Location]:
        # اصلاح نحوه بررسی نال در SQLAlchemy
        query = select(Location).options(
            selectinload(Location.children)
        ).where(Location.parent_id.is_(None))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_location_by_id(self, location_id: int) -> Optional[Location]:
        query = select(Location).options(
            selectinload(Location.children),
            selectinload(Location.posts)
        ).where(Location.id == location_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_location(self, location: Location, data: LocationUpdate) -> Location:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(location, key, value)
        await self.db.commit()
        await self.db.refresh(location)
        return await self.get_location_by_id(location.id)

    async def delete_location(self, location: Location) -> None:
        await self.db.delete(location)
        await self.db.commit()

    # ================= Post CRUD =================
    async def create_post(self, data: PostCreate) -> Post:
        post = Post(**data.model_dump())
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return await self.get_post_by_id(post.id)

    async def get_all_posts(self, skip: int = 0, limit: int = 100) -> List[Post]:
        query = select(Post).options(
            selectinload(Post.feeders),
            selectinload(Post.location)
        ).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_post_by_id(self, post_id: int) -> Optional[Post]:
        query = select(Post).options(
            selectinload(Post.feeders),
            selectinload(Post.location)
        ).where(Post.id == post_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_post(self, post: Post, data: PostUpdate) -> Post:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(post, key, value)
        await self.db.commit()
        await self.db.refresh(post)
        return await self.get_post_by_id(post.id)

    async def delete_post(self, post: Post) -> None:
        await self.db.delete(post)
        await self.db.commit()

    # ================= Feeder CRUD =================
    async def create_feeder(self, data: FeederCreate) -> Feeder:
        feeder = Feeder(**data.model_dump())
        self.db.add(feeder)
        await self.db.commit()
        await self.db.refresh(feeder)
        return feeder

    async def get_all_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Feeder]:
        query = select(Feeder).options(
            selectinload(Feeder.post)
        )
        if post_id:
            query = query.where(Feeder.post_id == post_id)
        query = query.offset(skip).limit(limit)
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

    # ================= Link CRUD =================
    async def create_link(self, data: LinkCreate) -> Link:
        link = Link(**data.model_dump())
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_all_links(self, skip: int = 0, limit: int = 100) -> List[Link]:
        query = select(Link).options(
            selectinload(Link.from_post),
            selectinload(Link.to_post)
        ).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_link_by_id(self, link_id: int) -> Optional[Link]:
        query = select(Link).options(
            selectinload(Link.from_post),
            selectinload(Link.to_post)
        ).where(Link.id == link_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_link(self, link: Link, data: LinkUpdate) -> Link:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(link, key, value)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def delete_link(self, link: Link) -> None:
        await self.db.delete(link)
        await self.db.commit()
