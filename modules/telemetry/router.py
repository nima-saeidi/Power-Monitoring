from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from modules.telemetry.ws_manager import telemetry_ws_manager
from modules.telemetry.schemas import TelemetryCreate
from modules.telemetry.service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# --- مسیر WebSocket ---
@router.websocket("/ws")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await telemetry_ws_manager.connect(websocket)
    try:
        while True:
            # اینجا فقط منتظر می‌مانیم تا کانکشن باز بماند
            # اگر فرانت‌اند پیامی بفرستد، اینجا دریافت می‌شود
            data = await websocket.receive_text()
            # در سیستم مانیتورینگ معمولاً فقط سرور دیتا می‌فرستد، اما می‌توانید اینجا لاجیک اضافه کنید
    except WebSocketDisconnect:
        telemetry_ws_manager.disconnect(websocket)


# --- مسیر REST برای تست اضافه کردن دیتا (معمولاً توسط اسکریپت Modbus صدا زده می‌شود) ---
@router.post("/record")
async def create_telemetry_record(
    data: TelemetryCreate,
    db: AsyncSession = Depends(get_db)
):
    service = TelemetryService(db)
    record = await service.add_telemetry_data(data)
    await db.commit()
    return {"message": "Data recorded and broadcasted successfully", "id": record.id}
