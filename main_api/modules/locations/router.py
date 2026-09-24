from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from main_api.core.database import get_db
from main_api.core.broker import RabbitMQPublisher

from main_api.modules.locations.repository import LocationRepository
from main_api.modules.locations.service import LocationService
from main_api.modules.locations.schemas import (
    LocationCreate, LocationUpdate, LocationResponse,
    CampusWithSubsectionsCreate, LocationFlatResponse
)
from main_api.modules.posts.schemas import PostResponse
from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin


locations_router = APIRouter(prefix="/locations", tags=["Locations (مکان‌ها)"])


async def get_message_broker():
    broker = RabbitMQPublisher()
    await broker.connect()
    try:
        yield broker
    finally:
        pass


def get_location_service(
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_message_broker)
) -> LocationService:
    repo = LocationRepository(db)
    return LocationService(repo=repo, broker=broker)


# =============================================================================
# Endpoints: Locations
# =============================================================================
@locations_router.post("/campus-with-subsections", response_model=LocationResponse, status_code=status.HTTP_201_CREATED,
                       summary="Create Campus and Subsections")
async def create_campus_with_subsections(data: CampusWithSubsectionsCreate,
                                         service: LocationService = Depends(get_location_service),
                                         current_user=Depends(require_tech_or_admin)):
    return await service.create_campus_with_subsections(data, username=current_user.email)


@locations_router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED,
                       summary="Create New Location")
async def create_location(data: LocationCreate, service: LocationService = Depends(get_location_service),
                          current_user=Depends(require_tech_or_admin)):
    return await service.create_location(data, username=current_user.email)


@locations_router.get("/roots", response_model=List[LocationResponse], summary="Get Root Locations")
async def get_root_locations(service: LocationService = Depends(get_location_service),
                             current_user=Depends(require_any_user)):
    return await service.get_root_locations()

@locations_router.get(
    "/flat",
    response_model=List[LocationFlatResponse],
    summary="Get All Locations (Flat List)"
)
async def get_locations_flat(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: LocationService = Depends(get_location_service),
    current_user = Depends(require_any_user)
):
    """
    دریافت لیست ساده و تخت از تمام مکان‌ها بدون ساختار درختی و زیرمجموعه‌ها
    """
    return await service.get_locations_flat(skip=skip, limit=limit)


@locations_router.get("", response_model=List[LocationResponse], summary="Get All Locations")
async def get_locations(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                        service: LocationService = Depends(get_location_service), current_user=Depends(require_any_user)):
    return await service.get_locations(skip=skip, limit=limit)


@locations_router.get("/{location_id}", response_model=LocationResponse, summary="Get Specific Location")
async def get_location(location_id: int, service: LocationService = Depends(get_location_service),
                       current_user=Depends(require_any_user)):
    return await service.get_location(location_id)


@locations_router.put("/{location_id}", response_model=LocationResponse, summary="Update Location")
async def update_location(location_id: int, data: LocationUpdate, service: LocationService = Depends(get_location_service),
                          current_user=Depends(require_tech_or_admin)):
    return await service.update_location(location_id, data, username=current_user.email)


@locations_router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Location")
async def delete_location(location_id: int, service: LocationService = Depends(get_location_service),
                          current_user=Depends(require_tech_or_admin)):
    await service.delete_location(location_id, username=current_user.email)
    return


@locations_router.get("/{location_id}/posts", response_model=List[PostResponse],
                      summary="Get all posts for a specific location")
async def get_posts_by_location(location_id: int, service: LocationService = Depends(get_location_service),
                                current_user=Depends(require_any_user)):
    return await service.get_posts_by_location(location_id)
