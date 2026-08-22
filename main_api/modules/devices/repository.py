from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# مدل‌ها و اسکیماها
from main_api.modules.devices.models import Post, Feeder, Location, Link
from main_api.modules.devices.schemas import (
    PostCreate, PostUpdate,
    FeederCreate, FeederUpdate,
    LocationCreate, LocationUpdate,
    LinkCreate, LinkUpdate
)


class DeviceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================
    # CREATE LOCATION
    # =========================================================

    async def create_location(self, data: LocationCreate) -> Location:
        location_data = data.model_dump(
            exclude={"sub_sections"},
            exclude_unset=True
        )

        location = Location(**location_data)
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)

        return location

    # =========================================================
    # GET ALL LOCATIONS AS TREE
    # =========================================================

    async def get_all_locations(self, skip: int = 0, limit: int = 100):
        stmt = select(Location).order_by(Location.id)
        result = await self.db.execute(stmt)
        locations = result.scalars().all()

        nodes = {}
        for location in locations:
            nodes[location.id] = {
                "id": location.id,
                "campus_name": location.name,
                "location_type": location.location_type,
                "parent_id": location.parent_id,
                "description": location.description,
                "address": location.address,  # فیلد جدید
                "sub_locations": []
            }

        roots = []
        for location in locations:
            node = nodes[location.id]
            if location.parent_id is None:
                roots.append(node)
            else:
                parent_node = nodes.get(location.parent_id)
                if parent_node:
                    parent_node["sub_locations"].append(node)

        roots = roots[skip: skip + limit]
        return roots

    # =========================================================
    # GET ROOT LOCATIONS
    # =========================================================

    async def get_root_locations(self):
        stmt = select(Location).order_by(Location.id)
        result = await self.db.execute(stmt)
        locations = result.scalars().all()

        nodes = {}
        for location in locations:
            nodes[location.id] = {
                "id": location.id,
                "campus_name": location.name,
                "location_type": location.location_type,
                "parent_id": location.parent_id,
                "description": location.description,
                "address": location.address,  # فیلد جدید
                "sub_locations": []
            }

        roots = []
        for location in locations:
            node = nodes[location.id]
            if location.parent_id is None:
                roots.append(node)
            else:
                parent_node = nodes.get(location.parent_id)
                if parent_node:
                    parent_node["sub_locations"].append(node)

        return roots

    # =========================================================
    # GET LOCATION BY ID
    # =========================================================

    async def get_location_by_id(self, location_id: int) -> Optional[dict]:
        # زنجیره selectinload برای واکشی تا ۴ سطح تو در تو
        stmt = (
            select(Location)
            .options(
                selectinload(Location.children)
                .selectinload(Location.children)
                .selectinload(Location.children)
            )
            .where(Location.id == location_id)
        )
        result = await self.db.execute(stmt)
        location = result.scalars().first()

        if not location:
            return None

        # تابع بازگشتی برای فرمت کردن خروجی
        def format_location(loc):
            sub_locations = []
            if 'children' in loc.__dict__:
                sub_locations = [format_location(child) for child in loc.children]

            return {
                "id": loc.id,
                "campus_name": loc.name,
                "location_type": loc.location_type,
                "parent_id": loc.parent_id,
                "description": loc.description,
                "address": loc.address,  # فیلد جدید
                "sub_locations": sub_locations
            }

        return format_location(location)

    # =========================================================
    # UPDATE LOCATION
    # =========================================================

    async def update_location(
            self,
            location_id: int,
            data: LocationUpdate
    ) -> Optional[Location]:

        stmt = select(Location).where(Location.id == location_id)
        result = await self.db.execute(stmt)
        location_obj = result.scalar_one_or_none()

        if not location_obj:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(location_obj, key, value)

        await self.db.commit()
        await self.db.refresh(location_obj)

        return location_obj

    # =========================================================
    # DELETE LOCATION
    # =========================================================

    async def delete_location(self, location_id: int) -> bool:
        query = select(Location).where(Location.id == location_id)
        result = await self.db.execute(query)
        location_obj = result.scalar_one_or_none()

        if location_obj:
            await self.db.delete(location_obj)
            await self.db.commit()
            return True

        return False

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

    async def get_all_links(self, skip: int = 0, limit: int = 100):
        query = select(Link).offset(skip).limit(limit)
        # در اینجا self.db_session اشتباه بود و به self.db تغییر یافت
        result = await self.db.execute(query)
        return result.scalars().all()


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
