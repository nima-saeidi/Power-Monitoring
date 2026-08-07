from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from core.database import get_db
from modules.devices.repository import DeviceRepository
from modules.devices.service import DeviceService
from modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, LocationResponse # اسکیماهای لوکیشن اضافه شد
)
from modules.auth.dependencies import get_current_user, get_tech_or_admin_user

router = APIRouter(prefix="/devices", tags=["مدیریت تجهیزات (لوکیشن، پست، فیدر، لینک)"])

def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    repo = DeviceRepository(db)
    return DeviceService(repo)

# ================= Endpoints: Locations =================

@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد مکان/لوکیشن جدید (ادمین/اپراتور)")
async def create_location(
    data: LocationCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.create_location(data)

@router.get("/locations/roots", response_model=List[LocationResponse], summary="دریافت مکان‌های ریشه (مناسب برای ساخت درخت UI)")
async def get_root_locations(
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_root_locations()

@router.get("/locations", response_model=List[LocationResponse], summary="دریافت لیست تمامی مکان‌ها")
async def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_locations(skip=skip, limit=limit)

@router.get("/locations/{location_id}", response_model=LocationResponse, summary="دریافت اطلاعات یک مکان خاص")
async def get_location(
    location_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_location(location_id)

@router.put("/locations/{location_id}", response_model=LocationResponse, summary="ویرایش مشخصات مکان (ادمین/اپراتور)")
async def update_location(
    location_id: int,
    data: LocationUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.update_location(location_id, data)

@router.delete("/locations/{location_id}", summary="حذف مکان (ادمین/اپراتور)")
async def delete_location(
    location_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.delete_location(location_id)

# ================= Endpoints: Posts =================

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد پست جدید (ادمین/اپراتور)")
async def create_post(
    data: PostCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.create_post(data)

@router.get("/posts", response_model=List[PostResponse], summary="دریافت لیست تمامی پست‌ها")
async def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_posts(skip=skip, limit=limit)

@router.get("/posts/{post_id}", response_model=PostResponse, summary="دریافت اطلاعات یک پست")
async def get_post(
    post_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_post(post_id)

@router.put("/posts/{post_id}", response_model=PostResponse, summary="ویرایش پست (ادمین/اپراتور)")
async def update_post(
    post_id: int,
    data: PostUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.update_post(post_id, data)

@router.delete("/posts/{post_id}", summary="حذف پست (ادمین/اپراتور)")
async def delete_post(
    post_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.delete_post(post_id)

# ================= Endpoints: Feeders =================

@router.post("/feeders", response_model=FeederResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد فیدر جدید (ادمین/اپراتور)")
async def create_feeder(
    data: FeederCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.create_feeder(data)

@router.get("/feeders", response_model=List[FeederResponse], summary="دریافت لیست فیدرها")
async def get_feeders(
    post_id: Optional[int] = Query(None, description="فیلتر بر اساس شناسه پست"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_feeders(post_id=post_id, skip=skip, limit=limit)

@router.get("/feeders/{feeder_id}", response_model=FeederResponse, summary="دریافت اطلاعات یک فیدر")
async def get_feeder(
    feeder_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_feeder(feeder_id)

@router.put("/feeders/{feeder_id}", response_model=FeederResponse, summary="ویرایش فیدر (ادمین/اپراتور)")
async def update_feeder(
    feeder_id: int,
    data: FeederUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.update_feeder(feeder_id, data)

@router.delete("/feeders/{feeder_id}", summary="حذف فیدر (ادمین/اپراتور)")
async def delete_feeder(
    feeder_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.delete_feeder(feeder_id)


# ================= Endpoints: Links =================

@router.post("/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, summary="ایجاد لینک جدید بین دو پست (ادمین/اپراتور)")
async def create_link(
    data: LinkCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.create_link(data)

@router.get("/links", response_model=List[LinkResponse], summary="دریافت لیست لینک‌ها")
async def get_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_links(skip=skip, limit=limit)

@router.get("/links/{link_id}", response_model=LinkResponse, summary="دریافت اطلاعات یک لینک")
async def get_link(
    link_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_link(link_id)

@router.put("/links/{link_id}", response_model=LinkResponse, summary="ویرایش مشخصات لینک (ادمین/اپراتور)")
async def update_link(
    link_id: int,
    data: LinkUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.update_link(link_id, data)

@router.delete("/links/{link_id}", summary="حذف لینک (ادمین/اپراتور)")
async def delete_link(
    link_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_tech_or_admin_user)
):
    return await service.delete_link(link_id)
