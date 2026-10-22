from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Literal, Optional

from main_api.core.database import get_db
from main_api.core.broker import RabbitMQPublisher, get_rabbitmq_publisher

from main_api.modules.links.repository import LinkRepository
from main_api.modules.links.service import LinkService
from main_api.modules.links.schemas import ActiveLinkSource, LinkCreate, LinkUpdate, LinkResponse
from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin, verify_internal_api_key


links_router = APIRouter(prefix="/links", tags=["Links (اتصالات شبکه)"])


def get_link_service(
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_rabbitmq_publisher)
) -> LinkService:
    repo = LinkRepository(db)
    return LinkService(repo=repo, broker=broker)


@links_router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, summary="Create New Link")
async def create_link(data: LinkCreate, service: LinkService = Depends(get_link_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.create_link(data, username=current_user.email)


@links_router.get("", response_model=List[LinkResponse], summary="Get All Links")
async def get_links(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                    post_id: Optional[int] = Query(None, description="لینک‌های متصل به این پست"),
                    is_active: Optional[bool] = Query(None),
                    load_status: Optional[Literal["normal", "warning", "critical", "unknown"]] = Query(None),
                    service: LinkService = Depends(get_link_service), current_user=Depends(require_any_user)):
    return await service.get_links(skip=skip, limit=limit, post_id=post_id, is_active=is_active,
                                   load_status=load_status)


@links_router.get("/internal/active-sources", response_model=List[ActiveLinkSource],
                  dependencies=[Depends(verify_internal_api_key)], include_in_schema=False)
async def get_active_link_sources(db: AsyncSession = Depends(get_db)):
    """Links with an `external_source` in their metadata, polled by link_ingestion_service."""
    links = await LinkRepository(db).get_active_links_with_source()
    sources = []
    for link in links:
        cfg = (link.metadata_info or {}).get("external_source") or {}
        if not isinstance(cfg, dict) or not cfg.get("provider") or not cfg.get("external_id"):
            continue
        sources.append(ActiveLinkSource(
            link_id=link.id,
            name=link.name,
            feeder_id=link.feeder_id,
            allowed_current=link.allowed_current,
            provider=cfg["provider"],
            external_id=str(cfg["external_id"]),
            interval=cfg.get("interval"),
            field_map=cfg.get("field_map") or {},
            options=cfg.get("options") or {},
        ))
    return sources


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
