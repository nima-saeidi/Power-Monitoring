from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.database import get_db
from main_api.modules.telemetry.service import TelemetryService
from main_api.modules.telemetry.schemas import ActiveFeederConfig
from main_api.modules.telemetry.ws_manager import ws_manager

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# --- اندپوینت دریافت لیست فیدرهای فعال برای میکروسرویس تلمتری (Worker) ---
@router.get("/active-feeders", response_model=List[ActiveFeederConfig])
async def get_active_feeders(db: AsyncSession = Depends(get_db)):
    service = TelemetryService(db)
    return await service.get_active_feeders()

# --- WebSocket Endpoint (برای نمودارهای زنده فرانت‌اند) ---
@router.websocket("/ws")
async def telemetry_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# --- REST Endpoints (پروکسی به میکروسرویس) ---
@router.get("/latest/{feeder_id}")
async def get_latest(feeder_id: str):
    return await TelemetryService.get_latest_telemetry(feeder_id)

@router.get("/history/{feeder_id}")
async def get_history(
    feeder_id: str,
    start: str = Query(default="-1h", description="Flux time format, e.g., -1h, -24h"),
    stop: str = Query(default="now()", description="Flux time format"),
    window: str = Query(default="1m", description="Aggregation window, e.g., 1m, 5m")
):
    return await TelemetryService.get_history(feeder_id, start, stop, window)

@router.get("/chart/{feeder_id}")
async def get_chart_data(
    feeder_id: str,
    start: str = Query(default="-24h", description="Flux time format or ISO datetime string"),
    stop: str = Query(default="now()", description="Flux time format or ISO datetime string"),
    window: str = Query(default="5m", description="Aggregation window, e.g., 1m, 5m, 1h")
):
    """
    دریافت داده‌های تفکیک‌شده نمودار (سری‌های زمانی + timestamps) پروکسی شده از میکروسرویس تلمتری
    """
    return await TelemetryService.get_chart_data(feeder_id, start, stop, window)
