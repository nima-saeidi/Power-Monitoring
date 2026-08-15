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
    LocationCreate, LocationUpdate, LocationResponse, CommandRequest  # Location schemas added
)
# Fixed import: replaced with require_tech_or_admin
from modules.auth.dependencies import get_current_user, require_tech_or_admin

from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO


router = APIRouter(prefix="/devices", tags=["Device Management (Location, Post, Feeder, Link)"])


def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    repo = DeviceRepository(db)
    return DeviceService(repo)


# ================= Endpoints: Locations =================

@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED, summary="Create New Location (Admin/Operator)")
async def create_location(
    data: LocationCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_location(data)


@router.get("/locations/roots", response_model=List[LocationResponse], summary="Get Root Locations (for building UI tree)")
async def get_root_locations(
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_root_locations()


@router.get("/locations", response_model=List[LocationResponse], summary="Get List of All Locations")
async def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_locations(skip=skip, limit=limit)


@router.get("/locations/{location_id}", response_model=LocationResponse, summary="Get Info of a Specific Location")
async def get_location(
    location_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_location(location_id)


@router.put("/locations/{location_id}", response_model=LocationResponse, summary="Update Location Details (Admin/Operator)")
async def update_location(
    location_id: int,
    data: LocationUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.update_location(location_id, data)


@router.delete("/locations/{location_id}", summary="Delete Location (Admin/Operator)")
async def delete_location(
    location_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.delete_location(location_id)


# ================= Endpoints: Posts =================

@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="Create New Post (Admin/Operator)")
async def create_post(
    data: PostCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_post(data)


@router.get("/posts", response_model=List[PostResponse], summary="Get List of All Posts")
async def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_posts(skip=skip, limit=limit)


@router.get("/posts/{post_id}", response_model=PostResponse, summary="Get Info of a Single Post")
async def get_post(
    post_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_post(post_id)


@router.put("/posts/{post_id}", response_model=PostResponse, summary="Update Post (Admin/Operator)")
async def update_post(
    post_id: int,
    data: PostUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.update_post(post_id, data)


@router.delete("/posts/{post_id}", summary="Delete Post (Admin/Operator)")
async def delete_post(
    post_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.delete_post(post_id)


# ================= Endpoints: Feeders =================

@router.get("/feeders/download-template", summary="Download Excel Template for Feeder Import")
async def download_feeder_excel_template(current_user = Depends(get_current_user)):
    """
    Download a sample Excel file (Template) to be used for bulk importing feeders.
    """
    # Sample columns based on your feeder schema
    template_data = {
        'post_id': [1, 2],  # ID of the post the feeder is connected to
        'name': ['Feeder Output No. 1', 'Feeder Input Transformer 2'],
        'ip_address': ['192.168.1.50', '192.168.1.51'],
        'port': [502, 502],
        'unit_id': [1, 1],
        'capacity_kva': [630, 800],
        'description': ['Test description 1', 'Test description 2']
    }

    df = pd.DataFrame(template_data)

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=feeders_template.xlsx"}
    )


@router.post("/feeders/import-excel", summary="Bulk Import Feeders from Excel File (Admin/Technician)")
async def import_feeders_from_excel(
    file: UploadFile = File(...),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    """
    Upload an Excel file based on the downloaded template and bulk-register feeders in the database.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File format must be Excel (.xlsx or .xls)")

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading the Excel file: {str(e)}")

    result = await service.import_feeders_from_excel(df)
    return result


@router.post("/feeders", response_model=FeederResponse, status_code=status.HTTP_201_CREATED, summary="Create New Feeder (Admin/Operator)")
async def create_feeder(
    data: FeederCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_feeder(data)


@router.get("/feeders", response_model=List[FeederResponse], summary="Get List of Feeders")
async def get_feeders(
    post_id: Optional[int] = Query(None, description="Filter by post ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_feeders(post_id=post_id, skip=skip, limit=limit)


@router.get("/feeders/{feeder_id}", response_model=FeederResponse, summary="Get Info of a Single Feeder")
async def get_feeder(
    feeder_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_feeder(feeder_id)


@router.put("/feeders/{feeder_id}", response_model=FeederResponse, summary="Update Feeder (Admin/Operator)")
async def update_feeder(
    feeder_id: int,
    data: FeederUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.update_feeder(feeder_id, data)


@router.delete("/feeders/{feeder_id}", summary="Delete Feeder (Admin/Operator)")
async def delete_feeder(
    feeder_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.delete_feeder(feeder_id)


# ================= Endpoints: Links =================

@router.post("/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED, summary="Create New Link Between Two Posts (Admin/Operator)")
async def create_link(
    data: LinkCreate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_link(data)


@router.get("/links", response_model=List[LinkResponse], summary="Get List of Links")
async def get_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_links(skip=skip, limit=limit)


@router.get("/links/{link_id}", response_model=LinkResponse, summary="Get Info of a Single Link")
async def get_link(
    link_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(get_current_user)
):
    return await service.get_link(link_id)


@router.put("/links/{link_id}", response_model=LinkResponse, summary="Update Link Details (Admin/Operator)")
async def update_link(
    link_id: int,
    data: LinkUpdate,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.update_link(link_id, data)


@router.delete("/links/{link_id}", summary="Delete Link (Admin/Operator)")
async def delete_link(
    link_id: int,
    service: DeviceService = Depends(get_device_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.delete_link(link_id)


@router.post("/feeders/{feeder_id}/command", summary="Send Control Command to Feeder")
async def send_command_to_feeder(
    feeder_id: int,
    request: CommandRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Takes a feeder ID and sends an open/close command (True/False) to the
    specified register via Modbus.
    """
    repo = DeviceRepository(db)
    service = DeviceService(repo)

    # Call the method we implemented in the service
    result = await service.execute_device_command(feeder_id, request)
    return result
