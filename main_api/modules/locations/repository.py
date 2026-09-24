from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.modules.locations.models import Location
from main_api.modules.locations.schemas import LocationCreate, LocationUpdate
from main_api.modules.posts.models import Post


class LocationRepository:

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
    # GET FLAT LOCATIONS (بدون ساختار درختی)
    # =========================================================
    async def get_all_locations_flat(self, skip: int = 0, limit: int = 100) -> List[Location]:
        stmt = (
            select(Location)
            .order_by(Location.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
                "address": location.address,
                "sub_locations": []
            }

        db_roots = []
        for location in locations:
            node = nodes[location.id]
            if location.parent_id is None:
                db_roots.append(node)
            else:
                parent_node = nodes.get(location.parent_id)
                if parent_node:
                    parent_node["sub_locations"].append(node)

        # اعمال pagination روی ریشه‌های دیتابیس
        paginated_roots = db_roots[skip: skip + limit]

        # اصلاح: خود لیست را برگردانید، نه داخل یک براکت دیگر
        return paginated_roots


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

    async def get_posts_by_location(self, location_id: int):
        stmt = (
            select(Post)
            .where(Post.location_id == location_id)
            .options(
                selectinload(Post.location),  # اضافه شدن لودِ لوکیشن برای رفع خطای MissingGreenlet
                selectinload(Post.feeders)    # اگر فیدرها هم در PostResponse هستند، این هم لازم است
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
