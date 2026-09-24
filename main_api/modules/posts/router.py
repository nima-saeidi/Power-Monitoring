from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from main_api.core.database import get_db
from main_api.core.broker import RabbitMQPublisher

from main_api.modules.posts.repository import PostRepository
from main_api.modules.posts.service import PostService
from main_api.modules.posts.schemas import PostCreate, PostUpdate, PostResponse
from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin


posts_router = APIRouter(prefix="/posts", tags=["Posts (پست‌های برق)"])


async def get_message_broker():
    broker = RabbitMQPublisher()
    await broker.connect()
    try:
        yield broker
    finally:
        pass


def get_post_service(
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_message_broker)
) -> PostService:
    repo = PostRepository(db)
    return PostService(repo=repo, broker=broker)


# =============================================================================
# Endpoints: Posts
# =============================================================================
@posts_router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="Create New Post")
async def create_post(data: PostCreate, service: PostService = Depends(get_post_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.create_post(data, username=current_user.email)


@posts_router.get("", response_model=List[PostResponse], summary="Get All Posts")
async def get_posts(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                    service: PostService = Depends(get_post_service), current_user=Depends(require_any_user)):
    return await service.get_posts(skip=skip, limit=limit)


@posts_router.get("/{post_id}", response_model=PostResponse, summary="Get Specific Post")
async def get_post(post_id: int, service: PostService = Depends(get_post_service),
                   current_user=Depends(require_any_user)):
    return await service.get_post(post_id)


@posts_router.put("/{post_id}", response_model=PostResponse, summary="Update Post")
async def update_post(post_id: int, data: PostUpdate, service: PostService = Depends(get_post_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.update_post(post_id, data, username=current_user.email)


@posts_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Post")
async def delete_post(post_id: int, service: PostService = Depends(get_post_service),
                      current_user=Depends(require_tech_or_admin)):
    await service.delete_post(post_id, username=current_user.email)
    return
