import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from modules.telemetry.schemas import (
    TelemetryCreate,
    TelemetryResponse,
    TelemetryChartResponse,
)
from modules.telemetry.service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


def parse_time_param(time_str: Optional[str], default_delta: Optional[timedelta] = None) -> datetime:
    """
    پارس کردن تاریخ هم به صورت عبارات نسبی (-24h, -30d, now()) و هم استاندارد ISO
    """
    now = datetime.now(timezone.utc)

    if not time_str or time_str.strip() in ("", "now", "now()"):
        if default_delta:
            return now - default_delta
        return now

    time_str = time_str.strip()

    # بررسی فرمت‌های نسبی مانند -24h, -30d, -15m, -60s
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

    # بررسی و تبدیل رشته استاندارد ISO
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        # اطمینان از داشتن timezone
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
        pattern="^(10s|30s|1m|5m|15m|1h|1d)$",
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


@router.get(
    "/chart/{feeder_id}",
    response_model=TelemetryChartResponse,
)
async def get_telemetry_chart(
    feeder_id: int,
    start: Optional[str] = Query(default="-24h", description="مانند -24h, -7d, -30d یا تاریخ ISO"),
    stop: Optional[str] = Query(default="now()", description="مانند now(), -1h یا تاریخ ISO"),
    window: str = Query(default="5m", pattern="^(10s|30s|1m|5m|15m|1h|1d)$"),
):
    """
    دریافت داده‌های ساختاریافته برای رسم نمودارهای تله‌متری
    """
    start_time = parse_time_param(start, default_delta=timedelta(days=1))
    end_time = parse_time_param(stop)

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
