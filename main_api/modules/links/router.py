from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from main_api.core.database import get_db
from main_api.core.broker import RabbitMQPublisher

from main_api.modules.links.repository import LinkRepository
from main_api.modules.links.service import LinkService
from main_api.modules.links.schemas import LinkCreate, LinkUpdate, LinkResponse
from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin


links_router = APIRouter(prefix="/links", tags=["Links (اتصالات شبکه)"])


async def get_message_broker():
    broker = RabbitMQPublisher()
    await broker.connect()
    try:
        yield broker
    finally:
        pass


def get_link_service(
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_message_broker)
) -> LinkService:
    repo = LinkRepository(db)
    return LinkService(repo=repo, broker=broker)


# =============================================================================
# Endpoints: Links
# =============================================================================
@links_router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, summary="Create New Link")
async def create_link(data: LinkCreate, service: LinkService = Depends(get_link_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.create_link(data, username=current_user.email)


@links_router.get("", response_model=List[LinkResponse], summary="Get All Links")
async def get_links(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                    service: LinkService = Depends(get_link_service), current_user=Depends(require_any_user)):
    return await service.get_links(skip=skip, limit=limit)


@links_router.get("/{link_id}", response_model=LinkResponse, summary="Get Specific Link")
async def get_link(link_id: int, service: LinkService = Depends(get_link_service),
                   current_user=Depends(require_any_user)):
    return await service.get_link(link_id)


@links_router.put("/{link_id}", response_model=LinkResponse, summary="Update Link")
async def update_link(link_id: int, data: LinkUpdate, service: LinkService = Depends(get_link_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.update_link(link_id, data, username=current_user.email)


@links_router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Link")
async def delete_link(link_id: int, service: LinkService = Depends(get_link_service),
                      current_user=Depends(require_tech_or_admin)):
    await service.delete_link(link_id, username=current_user.email)
    return
