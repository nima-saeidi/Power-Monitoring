from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from modules.telemetry.schemas import TelemetryCreate, TelemetryResponse
from modules.telemetry.service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


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

@router.get(
    "/chart/{feeder_id}",
    response_model=TelemetryChartResponse,
)
async def get_telemetry_chart(
    feeder_id: int,
    start: Optional[str] = Query(default="-30d"),
    stop: Optional[str] = Query(default="now()"),
    window: str = Query(default="5m"),
):
    now = datetime.now(timezone.utc)

    # تبدیل start
    if start in (None, "", "-30d"):
        start_time = now - timedelta(days=30)
    else:
        start_time = datetime.fromisoformat(
            start.replace("Z", "+00:00")
        )

    # تبدیل stop
    if stop in (None, "", "now()"):
        end_time = now
    else:
        end_time = datetime.fromisoformat(
            stop.replace("Z", "+00:00")
        )

    return await TelemetryRepository.get_chart_data(
        feeder_id=feeder_id,
        start_time=start_time,
        end_time=end_time,
        window_period=window,
    )