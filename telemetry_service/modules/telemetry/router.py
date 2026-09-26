import hmac
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from core.config import settings
from modules.telemetry import analytics
from modules.telemetry.modbus_client import ModbusReader
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse
from modules.telemetry.service import TelemetryService


async def verify_internal_api_key(x_internal_api_key: Optional[str] = Header(default=None)):
    """
    این سرویس فقط از main_api فراخوانی می‌شود (پورت 8001 در docker-compose بیرون باز است)،
    پس همه‌ی اندپوینت‌ها کلید مشترک INTERNAL_API_KEY را می‌خواهند.
    """
    expected = settings.INTERNAL_API_KEY
    if not expected or not x_internal_api_key or not hmac.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


router = APIRouter(prefix="/telemetry", tags=["Telemetry"], dependencies=[Depends(verify_internal_api_key)])

# حداکثر انتظار برای پاسخ دستگاه به فرمان قطع/وصل (ثانیه)
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
    """انرژی اکتیو (kWh) و راکتیو (kVARh) هر فیدر = انتگرال توان در بازه."""
    start_time, end_time = _resolve_range(start_time, end_time)
    energy = await analytics.get_energy(feeder_ids, start_time, end_time, window)
    return {"start_time": start_time, "end_time": end_time, "feeders": list(energy.values())}


@router.get("/forecast/{feeder_id}")
async def get_forecast(
    feeder_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    history_days: int = Query(default=7, ge=1, le=60),
):
    """پیش‌بینی ساعتی توان اکتیو و راکتیو (میانگین همان ساعت در روزهای گذشته)."""
    return await analytics.get_forecast(feeder_id, hours, history_days)


class CoilWriteRequest(BaseModel):
    ip_address: str = Field(..., max_length=50)
    port: int = Field(502, ge=1, le=65535)
    slave_id: int = Field(1, ge=0, le=247)
    register_address: int = Field(..., ge=0, le=65535)
    value: bool


@router.post("/command")
async def write_coil(data: CoilWriteRequest):
    """اجرای فرمان قطع/وصل روی دستگاه (نوشتن Coil). تأیید دومرحله‌ای در main_api انجام می‌شود."""
    reader = ModbusReader(host=data.ip_address, port=data.port, timeout=COMMAND_TIMEOUT_SECONDS, retries=2)
    try:
        ok = await reader.write_coil(data.register_address, data.value, slave=data.slave_id)
    finally:
        await reader.close()
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Device did not accept the command.")
    return {"success": True, "register_address": data.register_address, "value": data.value}



@router.post("/", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def create_telemetry_entry(data: TelemetryCreate):
    """
    ثبت دستی تله‌متری (یا دریافت از سنسورها/ایجنت‌ها)
    """
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
    """
    دریافت آخرین وضعیت و ۵ پارامتر الکتریکی فیدر
    """
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
        regex="^(10s|30s|1m|5m|15m|1h|1d)$",
        description="دوره فشرده‌سازی/میانگین داده‌ها"
    )
):
    """
    دریافت داده‌های تاریخی فیدر جهت رسم نمودارهای داشبورد و گزارش‌گیری
    """
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

from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse, TelemetryChartResponse

@router.get("/chart/{feeder_id}", response_model=TelemetryChartResponse)
async def get_feeder_chart_data(
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
        regex="^(10s|30s|1m|5m|15m|1h|1d)$",
        description="دوره فشرده‌سازی داده‌ها"
    )
):
    """
    دریافت داده‌های تفکیک‌شده بر اساس عنوان، مقادیر و آرایه زمان جهت استفاده مستقیم در کتابخانه‌های نمودار فرانت‌اند (مانند ApexCharts، Chart.js یا Highcharts)
    """
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

    chart_data = await TelemetryService.get_chart_data(
        feeder_id=feeder_id,
        start_time=start_time,
        end_time=end_time,
        window_period=window
    )
    return chart_data
