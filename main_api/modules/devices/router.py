import httpx
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import pandas as pd
from io import BytesIO
from typing import List
from main_api.core.database import get_db
from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.service import DeviceService
from main_api.modules.devices.schemas import (
    PostCreate, PostUpdate, PostResponse,
    FeederCreate, FeederUpdate, FeederResponse,
    LinkCreate, LinkUpdate, LinkResponse,
    LocationCreate, LocationUpdate, LocationResponse, CommandRequest,
    CampusWithSubsectionsCreate
)
from main_api.modules.auth.dependencies import get_current_user, require_tech_or_admin

locations_router = APIRouter(prefix="/locations", tags=["Locations (مکان‌ها)"])
posts_router = APIRouter(prefix="/posts", tags=["Posts (پست‌های برق)"])
feeders_router = APIRouter(prefix="/feeders", tags=["Feeders (فیدرها و تجهیزات)"])
links_router = APIRouter(prefix="/links", tags=["Links (اتصالات شبکه)"])


def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    repo = DeviceRepository(db)
    return DeviceService(repo)


# ================= Endpoints: Locations =================
@locations_router.post("/campus-with-subsections", response_model=LocationResponse, status_code=status.HTTP_201_CREATED,
                       summary="Create Campus and Subsections")
async def create_campus_with_subsections(data: CampusWithSubsectionsCreate,
                                         service: DeviceService = Depends(get_device_service),
                                         current_user=Depends(require_tech_or_admin)):
    return await service.create_campus_with_subsections(data)


@locations_router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED,
                       summary="Create New Location")
async def create_location(data: LocationCreate, service: DeviceService = Depends(get_device_service),
                          current_user=Depends(require_tech_or_admin)):
    return await service.create_location(data)


@locations_router.get("/roots", response_model=List[LocationResponse], summary="Get Root Locations")
async def get_root_locations(service: DeviceService = Depends(get_device_service),
                             current_user=Depends(get_current_user)):
    return await service.get_root_locations()


@locations_router.get("", response_model=List[LocationResponse], summary="Get All Locations")
async def get_locations(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                        service: DeviceService = Depends(get_device_service), current_user=Depends(get_current_user)):
    return await service.get_locations(skip=skip, limit=limit)


@locations_router.get("/{location_id}", response_model=LocationResponse, summary="Get Specific Location")
async def get_location(location_id: int, service: DeviceService = Depends(get_device_service),
                       current_user=Depends(get_current_user)):
    return await service.get_location(location_id)


@locations_router.put("/{location_id}", response_model=LocationResponse, summary="Update Location")
async def update_location(location_id: int, data: LocationUpdate, service: DeviceService = Depends(get_device_service),
                          current_user=Depends(require_tech_or_admin)):
    return await service.update_location(location_id, data)


@locations_router.delete("/{location_id}", summary="Delete Location")
async def delete_location(location_id: int, service: DeviceService = Depends(get_device_service),
                          current_user=Depends(require_tech_or_admin)):
    return await service.delete_location(location_id)


# ================= Endpoints: Posts =================
@posts_router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="Create New Post")
async def create_post(data: PostCreate, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.create_post(data)


@posts_router.get("", response_model=List[PostResponse], summary="Get All Posts")
async def get_posts(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                    service: DeviceService = Depends(get_device_service), current_user=Depends(get_current_user)):
    return await service.get_posts(skip=skip, limit=limit)


@posts_router.get("/{post_id}", response_model=PostResponse, summary="Get Specific Post")
async def get_post(post_id: int, service: DeviceService = Depends(get_device_service),
                   current_user=Depends(get_current_user)):
    return await service.get_post(post_id)


@posts_router.put("/{post_id}", response_model=PostResponse, summary="Update Post")
async def update_post(post_id: int, data: PostUpdate, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.update_post(post_id, data)


@posts_router.delete("/{post_id}", summary="Delete Post")
async def delete_post(post_id: int, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.delete_post(post_id)


# ================= Endpoints: Feeders =================
@feeders_router.get("/download-template", summary="Download Excel Template for Hierarchy Import")
async def download_feeder_excel_template(current_user=Depends(get_current_user)):
    # آپدیت ستون‌ها برای دریافت سلسله مراتب کامل: مکان -> پست -> فیدر
    template_data = {
        'campus_name': ['پردیس اصلی', 'پردیس اصلی'],
        'unit_name': ['دانشکده برق', 'دانشکده مکانیک'],
        'post_name': ['پست شماره ۱', 'پست شماره ۲'],
        'ip_address': ['192.168.1.10', '192.168.1.11'],
        'port': [502, 502],
        'supply_source': ['پست توزیع مرکزی', 'پست توزیع مرکزی'],
        'transformer_specs': ['20kV/400V 800kVA', '20kV/400V 630kVA'],
        'latitude': [38.068, 38.069],
        'longitude': [46.329, 46.330],
        'feeder_name': ['Feeder Output No. 1', 'Feeder Input Transformer 2'],
        'feeder_type': ['Producer', 'Consumer'],
        'max_current': [630.0, 800.0],
        'cable_type': ['Copper 3x120', 'Aluminum 3x185'],
        'modbus_address': [1, 2],
        'description': ['توضیحات تستی ۱', 'توضیحات تستی ۲']
    }
    df = pd.DataFrame(template_data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hierarchy_template.xlsx"}
    )



@feeders_router.post("/import-excel", summary="Bulk Import Feeders from Excel")
async def import_feeders_from_excel(file: UploadFile = File(...), service: DeviceService = Depends(get_device_service),
                                    current_user=Depends(require_tech_or_admin)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File format must be Excel (.xlsx or .xls)")
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading the Excel file: {str(e)}")
    return await service.import_feeders_from_excel(df)


@feeders_router.post("", response_model=List[FeederResponse], status_code=status.HTTP_201_CREATED,
                     summary="Create Multiple Feeders")
async def create_feeders(
    data: List[FeederCreate],
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_feeders(data)

@feeders_router.get("", response_model=List[FeederResponse], summary="Get All Feeders")
async def get_feeders(post_id: Optional[int] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                      service: DeviceService = Depends(get_device_service), current_user=Depends(get_current_user)):
    return await service.get_feeders(post_id=post_id, skip=skip, limit=limit)


@feeders_router.get("/{feeder_id}", response_model=FeederResponse, summary="Get Specific Feeder")
async def get_feeder(feeder_id: int, service: DeviceService = Depends(get_device_service),
                     current_user=Depends(get_current_user)):
    return await service.get_feeder(feeder_id)


@feeders_router.put("/{feeder_id}", response_model=FeederResponse, summary="Update Feeder")
async def update_feeder(feeder_id: int, data: FeederUpdate, service: DeviceService = Depends(get_device_service),
                        current_user=Depends(require_tech_or_admin)):
    return await service.update_feeder(feeder_id, data)


@feeders_router.delete("/{feeder_id}", summary="Delete Feeder")
async def delete_feeder(feeder_id: int, service: DeviceService = Depends(get_device_service),
                        current_user=Depends(require_tech_or_admin)):
    return await service.delete_feeder(feeder_id)


@feeders_router.post("/{feeder_id}/command", summary="Send Control Command to Feeder")
async def send_command_to_feeder(feeder_id: int, request: CommandRequest, db: AsyncSession = Depends(get_db),
                                 current_user=Depends(require_tech_or_admin)):
    repo = DeviceRepository(db)
    feeder = await repo.get_feeder_by_id(feeder_id)
    if not feeder:
        raise HTTPException(status_code=404, detail="Feeder not found")

    # مقادیر ارتباطی اکنون از Post مربوطه استخراج می‌شود
    if not feeder.post or not feeder.post.ip_address:
        raise HTTPException(status_code=400, detail="پست مربوط به این فیدر فاقد آدرس IP است.")

    TELEMETRY_SERVICE_URL = "http://telemetry_worker:8001/api/modbus/write"
    payload = {
        "ip_address": feeder.post.ip_address,
        "port": feeder.post.port if feeder.post.port else 502,
        "unit_id": feeder.post.unit_id if hasattr(feeder.post, 'unit_id') and feeder.post.unit_id else 1,
        "register_address": request.register_address,
        "value": request.value
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEMETRY_SERVICE_URL, json=payload, timeout=5.0)
        if response.status_code == 200:
            return {"status": "success", "detail": "Command executed successfully via Telemetry Service"}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to execute command on hardware")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Telemetry Service is unreachable: {str(e)}")


# ================= Endpoints: Links =================
@links_router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, summary="Create New Link")
async def create_link(data: LinkCreate, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.create_link(data)


@links_router.get("", response_model=List[LinkResponse], summary="Get All Links")
async def get_links(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                    service: DeviceService = Depends(get_device_service), current_user=Depends(get_current_user)):
    return await service.get_links(skip=skip, limit=limit)


@links_router.get("/{link_id}", response_model=LinkResponse, summary="Get Specific Link")
async def get_link(link_id: int, service: DeviceService = Depends(get_device_service),
                   current_user=Depends(get_current_user)):
    return await service.get_link(link_id)


@links_router.put("/{link_id}", response_model=LinkResponse, summary="Update Link")
async def update_link(link_id: int, data: LinkUpdate, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.update_link(link_id, data)


@links_router.delete("/{link_id}", summary="Delete Link")
async def delete_link(link_id: int, service: DeviceService = Depends(get_device_service),
                      current_user=Depends(require_tech_or_admin)):
    return await service.delete_link(link_id)
