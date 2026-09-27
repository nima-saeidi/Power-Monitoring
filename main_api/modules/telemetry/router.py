from typing import List, Literal, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from main_api.core.database import get_db
from main_api.core.rate_limit import limiter, EXPORT_LIMIT
from main_api.modules.auth.dependencies import (
    authenticate_websocket, require_page, verify_internal_api_key,
)
from main_api.modules.feeders.models import Feeder
from main_api.modules.telemetry.live import role_of
from main_api.modules.telemetry.report_export import (
    EXPORT_TIMEOUT_SECONDS,
    MAX_EXCEL_ROWS,
    MAX_PDF_ROWS,
    ReportSection,
    build_excel_report,
    build_pdf_report,
    resolve_columns,
)
from main_api.modules.telemetry.schemas import ActiveFeederConfig, FeederStatusUpdate
from main_api.modules.telemetry.service import TelemetryService
from main_api.modules.telemetry.ws_manager import ws_manager

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.get("/active-feeders", response_model=List[ActiveFeederConfig],
            dependencies=[Depends(verify_internal_api_key)])
async def get_active_feeders(db: AsyncSession = Depends(get_db)):
    service = TelemetryService(db)
    return await service.get_active_feeders()


@router.post("/feeder-status", status_code=204, dependencies=[Depends(verify_internal_api_key)])
async def report_feeder_status(
    data: FeederStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TelemetryService(db)
    await service.report_feeder_status(data)

@router.websocket("/ws")
async def telemetry_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    feeder_id: int | None = Query(default=None),
):
    if not await authenticate_websocket(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws_manager.connect(websocket, feeder_id)
    try:
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@router.get("/latest/{feeder_id}")
async def get_latest(
    feeder_id: str,
    current_user=Depends(require_page("telemetry"))
):
    return await TelemetryService.get_latest_telemetry(feeder_id)

@router.get("/history/{feeder_id}")
async def get_history(
    feeder_id: str,
    start: str = Query(default="-1h", description="زمان نسبی (-1h، -7d)، now() یا ISO"),
    stop: str = Query(default="now()", description="زمان نسبی، now() یا ISO"),
    window: str = Query(default="1m", description="Aggregation window, e.g., 1m, 5m"),
    current_user=Depends(require_page("telemetry"))
):
    return await TelemetryService.get_history(feeder_id, start, stop, window)

@router.get("/chart/{feeder_id}")
async def get_chart_data(
    feeder_id: str,
    start: str = Query(default="-24h", description="زمان نسبی (-1h، -7d)، now() یا ISO"),
    stop: str = Query(default="now()", description="زمان نسبی، now() یا ISO"),
    window: str = Query(default="5m", description="Aggregation window, e.g., 1m, 5m, 1h"),
    current_user=Depends(require_page("telemetry"))
):
    return await TelemetryService.get_chart_data(feeder_id, start, stop, window)


@router.get("/forecast/{feeder_id}", summary="Hourly active/reactive power forecast")
async def get_forecast(
    feeder_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    history_days: int = Query(default=7, ge=1, le=60),
    current_user=Depends(require_page("telemetry"))
):
    return await TelemetryService.get_forecast(feeder_id, hours, history_days)


@router.get("/energy", summary="Consumed/produced energy (kWh) per feeder, post, or type")
async def get_energy(
    feeder_ids: Optional[List[int]] = Query(default=None, description="یک یا چند فیدر"),
    post_id: Optional[int] = Query(default=None, description="همه‌ی فیدرهای این پست"),
    start: str = Query(default="-24h"),
    stop: str = Query(default="now()"),
    window: Optional[str] = Query(default=None, pattern="^(1h|1d|1w|1mo)$", description="سری انرژی به تفکیک بازه"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_page("reports"))
):
    feeders = await _load_feeders(db, feeder_ids, post_id)
    energy = await TelemetryService.get_energy([f.id for f in feeders], start, stop, window)
    rows = _energy_rows(feeders, energy)
    totals = {"consumption_kwh": 0.0, "production_kwh": 0.0, "unclassified_kwh": 0.0}
    for row in rows:
        key = {"consumer": "consumption_kwh", "producer": "production_kwh"}.get(row["role"], "unclassified_kwh")
        totals[key] = round(totals[key] + row["active_energy_kwh"], 3)
    return {"start_time": energy["start_time"], "end_time": energy["end_time"], "totals": totals, "feeders": rows}


@router.get("/report/{fmt}", summary="Telemetry report for one or more feeders (Excel/PDF)")
@limiter.limit(EXPORT_LIMIT)
async def export_report(
    request: Request,
    fmt: Literal["excel", "pdf"],
    feeder_ids: Optional[List[int]] = Query(default=None, description="یک یا چند فیدر"),
    post_id: Optional[int] = Query(default=None, description="همه‌ی فیدرهای این پست"),
    start: str = Query(default="-24h", description="زمان نسبی (-1h، -7d)، now() یا ISO"),
    stop: str = Query(default="now()", description="زمان نسبی، now() یا ISO"),
    window: str = Query(default="5m", description="دقت داده: 10s, 30s, 1m, 5m, 15m, 1h, 1d"),
    columns: Optional[List[str]] = Query(default=None, description="ستون‌های گزارش؛ خالی یعنی همه"),
    include_energy: bool = Query(default=True, description="افزودن خلاصه‌ی انرژی (kWh)"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_page("reports"))
):
    feeders = await _load_feeders(db, feeder_ids, post_id)
    return await _build_report(fmt, feeders, start, stop, window, columns, include_energy)


async def _load_feeders(db: AsyncSession, feeder_ids: Optional[List[int]], post_id: Optional[int]) -> List[Feeder]:
    query = select(Feeder).options(selectinload(Feeder.post)).order_by(Feeder.id)
    if feeder_ids:
        query = query.where(Feeder.id.in_(feeder_ids))
    if post_id is not None:
        query = query.where(Feeder.post_id == post_id)
    feeders = list((await db.execute(query)).scalars().all())
    if not feeders:
        raise HTTPException(status_code=404, detail="هیچ فیدری با این مشخصات پیدا نشد.")
    if feeder_ids and len(feeders) != len(set(feeder_ids)):
        missing = sorted(set(feeder_ids) - {f.id for f in feeders})
        raise HTTPException(status_code=404, detail=f"فیدر(های) {missing} پیدا نشد.")
    return feeders


def _energy_rows(feeders: List[Feeder], energy: dict) -> List[dict]:
    by_id = {row["feeder_id"]: row for row in energy.get("feeders", [])}
    return [
        {
            "feeder_id": f.id,
            "feeder_name": f.name,
            "post_id": f.post_id,
            "role": role_of(f),
            "active_energy_kwh": by_id.get(f.id, {}).get("active_energy_kwh", 0.0),
            "reactive_energy_kvarh": by_id.get(f.id, {}).get("reactive_energy_kvarh", 0.0),
            "series": by_id.get(f.id, {}).get("series", []),
        }
        for f in feeders
    ]


async def _build_report(fmt: str, feeders: List[Feeder], start: str, stop: str, window: str,
                        columns: Optional[List[str]], include_energy: bool) -> StreamingResponse:
    try:
        selected = resolve_columns(columns)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    max_rows = MAX_EXCEL_ROWS if fmt == "excel" else MAX_PDF_ROWS
    sections, total_rows = [], 0
    for feeder in feeders:
        records = await TelemetryService.get_history(str(feeder.id), start, stop, window, timeout=EXPORT_TIMEOUT_SECONDS)
        total_rows += len(records)
        if total_rows > max_rows:
            raise HTTPException(status_code=413, detail=(
                f"Result set too large (more than {max_rows} rows for {fmt}). "
                "Narrow the time range, use a coarser window, fewer feeders, or export as Excel."
            ))
        sections.append(ReportSection(title=f"{feeder.id} - {feeder.name}", records=records))
    if total_rows == 0:
        raise HTTPException(status_code=404, detail="No telemetry data found for the requested range.")

    energy = None
    if include_energy:
        energy_data = await TelemetryService.get_energy([f.id for f in feeders], start, stop, timeout=EXPORT_TIMEOUT_SECONDS)
        energy = _energy_rows(feeders, energy_data)

    name = f"feeder_{feeders[0].id}" if len(feeders) == 1 else f"feeders_{len(feeders)}"
    if fmt == "excel":
        output = build_excel_report(sections, selected, energy)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={name}_report.xlsx"},
        )
    output = build_pdf_report(sections, start, stop, selected, energy)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={name}_report.pdf"},
    )
