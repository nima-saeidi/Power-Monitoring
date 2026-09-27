import hmac
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from core.config import settings
from modules.telemetry import analytics
from modules.telemetry.modbus_client import ModbusReader
from modules.telemetry.schemas import (
    TelemetryCreate,
    TelemetryResponse,
    TelemetryChartResponse,
)
from modules.telemetry.service import TelemetryService


async def verify_internal_api_key(x_internal_api_key: Optional[str] = Header(default=None)):
    expected = settings.INTERNAL_API_KEY
    if not expected or not x_internal_api_key or not hmac.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


router = APIRouter(prefix="/telemetry", tags=["Telemetry"], dependencies=[Depends(verify_internal_api_key)])

COMMAND_TIMEOUT_SECONDS = 3


def _resolve_range(start_time: Optional[datetime], end_time: Optional[datetime]) -> tuple[datetime, datetime]:
    end_time = end_time or datetime.now(timezone.utc)
    start_time = start_time or end_time - timedelta(hours=24)
    if start_time >= end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be before end_time")
    return start_time, end_time


@router.get("/energy")
async def get_energy(
    feeder_ids: List[int] = Query(..., description="یک یا چند شناسه‌ی فیدر"),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    window: Optional[str] = Query(default=None, pattern="^(1h|1d|1w|1mo)$", description="سری انرژی به تفکیک بازه"),
):
    start_time, end_time = _resolve_range(start_time, end_time)
    energy = await analytics.get_energy(feeder_ids, start_time, end_time, window)
    return {"start_time": start_time, "end_time": end_time, "feeders": list(energy.values())}


@router.get("/forecast/{feeder_id}")
async def get_forecast(
    feeder_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    history_days: int = Query(default=7, ge=1, le=60),
):
    return await analytics.get_forecast(feeder_id, hours, history_days)


class CoilWriteRequest(BaseModel):
    ip_address: str = Field(..., max_length=50)
    port: int = Field(502, ge=1, le=65535)
    slave_id: int = Field(1, ge=0, le=247)
    register_address: int = Field(..., ge=0, le=65535)
    value: bool


@router.post("/command")
async def write_coil(data: CoilWriteRequest):
    reader = ModbusReader(host=data.ip_address, port=data.port, timeout=COMMAND_TIMEOUT_SECONDS, retries=2)
    try:
        ok = await reader.write_coil(data.register_address, data.value, slave=data.slave_id)
    finally:
        await reader.close()
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Device did not accept the command.")
    return {"success": True, "register_address": data.register_address, "value": data.value}



def parse_time_param(time_str: Optional[str], default_delta: Optional[timedelta] = None) -> datetime:
    now = datetime.now(timezone.utc)

    if not time_str or time_str.strip() in ("", "now", "now()"):
        if default_delta:
            return now - default_delta
        return now

    time_str = time_str.strip()

    relative_match = re.match(r"^-(\d+)([smhd])$", time_str)
    if relative_match:
        value, unit = int(relative_match.group(1)), relative_match.group(2)
        if unit == "s":
            return now - timedelta(seconds=value)
        elif unit == "m":
            return now - timedelta(minutes=value)
        elif unit == "h":
            return now - timedelta(hours=value)
        elif unit == "d":
            return now - timedelta(days=value)

    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"فرمت زمان نامعتبر است: '{time_str}'. از عبارات نسبی مانند -24h, -30d یا استاندارد ISO استفاده کنید."
        )


@router.post("/", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def create_telemetry_entry(data: TelemetryCreate):
    try:
        result = await TelemetryService.process_and_store(data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process telemetry: {str(e)}"
        )


@router.get("/latest/{feeder_id}", response_model=TelemetryResponse)
async def get_feeder_latest_telemetry(feeder_id: int):
    record = await TelemetryService.get_latest_telemetry(feeder_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry data found for feeder {feeder_id}"
        )
    return record


@router.get("/history/{feeder_id}", response_model=List[TelemetryResponse])
async def get_feeder_history(
    feeder_id: int,
    start_time: Optional[datetime] = Query(
        default=None,
        description="زمان شروع (پیش‌فرض: ۲۴ ساعت گذشته)"
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="زمان پایان (پیش‌فرض: اکنون)"
    ),
    window: str = Query(
        default="5m",
        pattern="^(10s|30s|1m|5m|15m|1h|1d)$",
        description="دوره فشرده‌سازی/میانگین داده‌ها"
    )
):
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be before end_time"
        )

    records = await TelemetryService.get_telemetry_history(
        feeder_id=feeder_id,
        start_time=start_time,
        end_time=end_time,
        window_period=window
    )
    return records


@router.get(
    "/chart/{feeder_id}",
    response_model=TelemetryChartResponse,
)
async def get_telemetry_chart(
    feeder_id: int,
    start: Optional[str] = Query(default="-24h", description="مانند -24h, -7d, -30d یا تاریخ ISO"),
    stop: Optional[str] = Query(default="now()", description="مانند now(), -1h یا تاریخ ISO"),
    window: str = Query(default="5m", pattern="^(10s|30s|1m|5m|15m|1h|1d)$"),
    start_time: Optional[datetime] = Query(default=None, description="زمان دقیق شروع (main_api این را می‌فرستد)"),
    end_time: Optional[datetime] = Query(default=None, description="زمان دقیق پایان"),
):
    start_time = start_time or parse_time_param(start, default_delta=timedelta(days=1))
    end_time = end_time or parse_time_param(stop)

    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="زمان شروع (start) باید قبل از زمان پایان (stop) باشد."
        )

    return await TelemetryService.get_chart_data(
        feeder_id=feeder_id,
        start_time=start_time,
        end_time=end_time,
        window_period=window,
    )
