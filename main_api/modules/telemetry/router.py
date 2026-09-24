from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.database import get_db
from main_api.modules.telemetry.service import TelemetryService
from main_api.modules.telemetry.schemas import ActiveFeederConfig, FeederStatusUpdate
from main_api.modules.telemetry.ws_manager import ws_manager
from main_api.modules.telemetry.report_export import (
    build_excel_report,
    build_pdf_report,
    EXPORT_TIMEOUT_SECONDS,
    MAX_EXCEL_ROWS,
    MAX_PDF_ROWS,
)

# ایمپورت دپندنسی‌های احراز هویت
from main_api.modules.auth.dependencies import require_any_user

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# --- اندپوینت دریافت لیست فیدرهای فعال برای میکروسرویس تلمتری (Worker) ---
# این اندپوینت بدون احراز هویت (بدون Depends) باقی می‌ماند
@router.get("/active-feeders", response_model=List[ActiveFeederConfig])
async def get_active_feeders(db: AsyncSession = Depends(get_db)):
    service = TelemetryService(db)
    return await service.get_active_feeders()


# --- اندپوینت داخلی: گزارش نتیجه Polling هر فیدر توسط telemetry_service ---
# مانند /active-feeders این اندپوینت هم بین دو میکروسرویس داخلی (پشت شبکه docker)
# فراخوانی می‌شود، نه از فرانت‌اند، پس بدون احراز هویت باقی می‌ماند.
@router.post("/feeder-status", status_code=204)
async def report_feeder_status(
    data: FeederStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TelemetryService(db)
    await service.report_feeder_status(data)

# --- WebSocket Endpoint (برای نمودارهای زنده فرانت‌اند) ---
@router.websocket("/ws")
async def telemetry_websocket(websocket: WebSocket):
    # نکته: احراز هویت با هدر (Bearer Token) در وب‌سوکت‌های مرورگر پشتیبانی نمی‌شود.
    # معمولاً توکن باید از طریق Query Parameter (مثلاً ws://...?token=...) دریافت و اینجا اعتبارسنجی شود.
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# --- REST Endpoints (پروکسی به میکروسرویس) ---
@router.get("/latest/{feeder_id}")
async def get_latest(
    feeder_id: str,
    current_user = Depends(require_any_user) # اضافه شدن احراز هویت
):
    return await TelemetryService.get_latest_telemetry(feeder_id)

@router.get("/history/{feeder_id}")
async def get_history(
    feeder_id: str,
    start: str = Query(default="-1h", description="Flux time format, e.g., -1h, -24h"),
    stop: str = Query(default="now()", description="Flux time format"),
    window: str = Query(default="1m", description="Aggregation window, e.g., 1m, 5m"),
    current_user = Depends(require_any_user) # اضافه شدن احراز هویت
):
    return await TelemetryService.get_history(feeder_id, start, stop, window)

@router.get("/chart/{feeder_id}")
async def get_chart_data(
    feeder_id: str,
    start: str = Query(default="-24h", description="Flux time format or ISO datetime string"),
    stop: str = Query(default="now()", description="Flux time format or ISO datetime string"),
    window: str = Query(default="5m", description="Aggregation window, e.g., 1m, 5m, 1h"),
    current_user = Depends(require_any_user) # اضافه شدن احراز هویت
):
    """
    دریافت داده‌های تفکیک‌شده نمودار (سری‌های زمانی + timestamps) پروکسی شده از میکروسرویس تلمتری
    """
    return await TelemetryService.get_chart_data(feeder_id, start, stop, window)


# --- خروجی گزارش (اکسل / PDF) ---
@router.get("/export/excel/{feeder_id}", summary="Export feeder telemetry report as Excel")
async def export_feeder_report_excel(
    feeder_id: str,
    start: str = Query(default="-24h", description="Flux time format or ISO datetime string"),
    stop: str = Query(default="now()", description="Flux time format or ISO datetime string"),
    window: str = Query(default="5m", description="Aggregation window, e.g., 1m, 5m, 1h"),
    current_user = Depends(require_any_user)
):
    """
    دریافت گزارش تاریخی فیدر و خروجی گرفتن آن به‌صورت فایل Excel (.xlsx)
    """
    # timeout بزرگ‌تر از حالت نمایش زنده چون کوئری InfluxDB روی بازه‌های بزرگ طولانی‌تر است
    records = await TelemetryService.get_history(feeder_id, start, stop, window, timeout=EXPORT_TIMEOUT_SECONDS)
    if not records:
        raise HTTPException(status_code=404, detail="No telemetry data found for the requested range.")
    if len(records) > MAX_EXCEL_ROWS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Result set too large ({len(records)} rows, max {MAX_EXCEL_ROWS}). "
                "Narrow the time range or use a coarser aggregation window."
            ),
        )

    output = build_excel_report(feeder_id, records)
    filename = f"feeder_{feeder_id}_report.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/pdf/{feeder_id}", summary="Export feeder telemetry report as PDF")
async def export_feeder_report_pdf(
    feeder_id: str,
    start: str = Query(default="-24h", description="Flux time format or ISO datetime string"),
    stop: str = Query(default="now()", description="Flux time format or ISO datetime string"),
    window: str = Query(default="5m", description="Aggregation window, e.g., 1m, 5m, 1h"),
    current_user = Depends(require_any_user)
):
    """
    دریافت گزارش تاریخی فیدر و خروجی گرفتن آن به‌صورت فایل PDF
    """
    records = await TelemetryService.get_history(feeder_id, start, stop, window, timeout=EXPORT_TIMEOUT_SECONDS)
    if not records:
        raise HTTPException(status_code=404, detail="No telemetry data found for the requested range.")
    if len(records) > MAX_PDF_ROWS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Result set too large for PDF ({len(records)} rows, max {MAX_PDF_ROWS}). "
                "Narrow the time range, use a coarser aggregation window, or export as Excel instead."
            ),
        )

    output = build_pdf_report(feeder_id, records, start, stop)
    filename = f"feeder_{feeder_id}_report.pdf"
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
