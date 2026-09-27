from fastapi import APIRouter, Depends, Request, status, Query, UploadFile, File, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Union, Literal
import pandas as pd
from io import BytesIO

from main_api.core.database import get_db
from main_api.core.rate_limit import limiter, IMPORT_LIMIT, COMMAND_LIMIT
from main_api.core.broker import RabbitMQPublisher

from main_api.modules.feeders.repository import FeederRepository
from main_api.modules.feeders.service import FeederService
from main_api.modules.feeders import commands
from main_api.modules.feeders.excel_import import TEMPLATE_ROW
from main_api.modules.feeders.schemas import (
    FeederCreate, FeederUpdate, FeederResponse, CommandRequest, CommandChallengeResponse, CommandConfirmRequest,
)
from main_api.modules.auth.dependencies import require_any_user, require_tech_or_admin


feeders_router = APIRouter(prefix="/feeders", tags=["Feeders (فیدرها و تجهیزات)"])

MAX_IMPORT_FILE_BYTES = 5 * 1024 * 1024


async def get_message_broker():
    broker = RabbitMQPublisher()
    await broker.connect()
    try:
        yield broker
    finally:
        pass


def get_feeder_service(
    db: AsyncSession = Depends(get_db),
    broker: RabbitMQPublisher = Depends(get_message_broker)
) -> FeederService:
    repo = FeederRepository(db)
    return FeederService(repo=repo, broker=broker)


@feeders_router.get("/download-template", summary="Download Excel Template for Hierarchy Import")
async def download_feeder_excel_template(current_user=Depends(require_any_user)):
    df = pd.DataFrame([TEMPLATE_ROW])
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=hierarchy_template.xlsx"})


@feeders_router.post("/import-excel", summary="Bulk Import Feeders from Excel")
@limiter.limit(IMPORT_LIMIT)
async def import_feeders_from_excel(request: Request, file: UploadFile = File(...),
                                    service: FeederService = Depends(get_feeder_service),
                                    current_user=Depends(require_tech_or_admin)):
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File format must be Excel (.xlsx or .xls)")
    contents = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    if len(contents) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Excel file is too large (max 5 MB).")
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Error reading the Excel file: the file is invalid or corrupted.")
    return await service.import_feeders_from_excel(df, username=current_user.email)


@feeders_router.post(
    "",
    response_model=Union[List[FeederResponse], FeederResponse],
    status_code=status.HTTP_201_CREATED,
    summary="ایجاد فیدر جدید (تکی یا گروهی)"
)
async def create_feeder(
    data: Union[List[FeederCreate], FeederCreate] = Body(...),
    service: FeederService = Depends(get_feeder_service),
    current_user = Depends(require_tech_or_admin)
):
    return await service.create_feeders(data, username=current_user.email)


@feeders_router.get("", response_model=List[FeederResponse], summary="Get All Feeders")
async def get_feeders(post_id: Optional[int] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                      feeder_type: Optional[Literal["consumer", "producer"]] = Query(None),
                      is_active: Optional[bool] = Query(None),
                      is_online: Optional[bool] = Query(None),
                      load_status: Optional[Literal["normal", "warning", "critical", "unknown"]] = Query(None),
                      search: Optional[str] = Query(None, max_length=100),
                      service: FeederService = Depends(get_feeder_service), current_user=Depends(require_any_user)):
    return await service.get_feeders(post_id=post_id, skip=skip, limit=limit, feeder_type=feeder_type,
                                     is_active=is_active, is_online=is_online, load_status=load_status, search=search)


@feeders_router.get("/{feeder_id}", response_model=FeederResponse, summary="Get Specific Feeder")
async def get_feeder(feeder_id: int, service: FeederService = Depends(get_feeder_service),
                     current_user=Depends(require_any_user)):
    return await service.get_feeder(feeder_id)


@feeders_router.put("/{feeder_id}", response_model=FeederResponse, summary="Update Feeder")
async def update_feeder(feeder_id: int, data: FeederUpdate, service: FeederService = Depends(get_feeder_service),
                        current_user=Depends(require_tech_or_admin)):
    return await service.update_feeder(feeder_id, data, username=current_user.email)


@feeders_router.delete("/{feeder_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Feeder")
async def delete_feeder(feeder_id: int, service: FeederService = Depends(get_feeder_service),
                        current_user=Depends(require_tech_or_admin)):
    await service.delete_feeder(feeder_id, username=current_user.email)
    return


@feeders_router.post("/{feeder_id}/command/request", response_model=CommandChallengeResponse,
                     summary="Request a connect/disconnect command (emails a confirmation code)")
@limiter.limit(COMMAND_LIMIT)
async def request_feeder_command(request: Request, feeder_id: int, data: CommandRequest,
                                 db: AsyncSession = Depends(get_db), current_user=Depends(require_tech_or_admin)):
    feeder = await FeederRepository(db).get_feeder_by_id(feeder_id)
    if not feeder:
        raise HTTPException(status_code=404, detail="Feeder not found")
    return await commands.request_command(feeder, data.action, current_user)


@feeders_router.post("/{feeder_id}/command/confirm", summary="Confirm and execute a connect/disconnect command")
@limiter.limit(COMMAND_LIMIT)
async def confirm_feeder_command(request: Request, feeder_id: int, data: CommandConfirmRequest,
                                 db: AsyncSession = Depends(get_db), current_user=Depends(require_tech_or_admin)):
    feeder = await FeederRepository(db).get_feeder_by_id(feeder_id)
    if not feeder:
        raise HTTPException(status_code=404, detail="Feeder not found")
    return await commands.confirm_command(feeder, data, current_user)
