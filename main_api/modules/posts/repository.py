from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.modules.posts.models import Post
from main_api.modules.posts.schemas import PostCreate, PostUpdate


class PostRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

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
