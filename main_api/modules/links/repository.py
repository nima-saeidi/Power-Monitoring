from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.modules.links.models import Link
from main_api.modules.links.schemas import LinkCreate, LinkUpdate
from main_api.modules.posts.models import Post


class LinkRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_link(self, data: LinkCreate) -> Link:
        link = Link(**data.model_dump())
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        # تغییر مهم: لینک را همراه با تمام جزئیات پست‌ها واکشی و برمی‌گردانیم
        return await self.get_link_by_id(link.id)

    async def get_all_links(self, skip: int = 0, limit: int = 100):
        query = select(Link).options(
            # بارگذاری پست مبدأ به همراه فیدرها و مکان آن
            selectinload(Link.from_post).selectinload(Post.feeders),
            selectinload(Link.from_post).selectinload(Post.location),

            # بارگذاری پست مقصد به همراه فیدرها و مکان آن
            selectinload(Link.to_post).selectinload(Post.feeders),
            selectinload(Link.to_post).selectinload(Post.location)
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_link_by_id(self, link_id: int) -> Optional[Link]:
        query = select(Link).options(
            # بارگذاری زنجیره‌ای فیلدهای تو در تو
            selectinload(Link.from_post).selectinload(Post.feeders),
            selectinload(Link.from_post).selectinload(Post.location),

            selectinload(Link.to_post).selectinload(Post.feeders),
            selectinload(Link.to_post).selectinload(Post.location)
        ).where(Link.id == link_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_link(self, link: Link, data: LinkUpdate) -> Link:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(link, key, value)
        await self.db.commit()
        await self.db.refresh(link)
        # تغییر مهم: بعد از آپدیت، مجدداً با جزئیات کامل برمی‌گردانیم
        return await self.get_link_by_id(link.id)

    async def delete_link(self, link: Link) -> None:
        """
        حذف یک لینک از دیتابیس
        """
        await self.db.delete(link)
        await self.db.commit()
