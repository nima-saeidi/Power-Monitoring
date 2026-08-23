from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

# ایمپورت‌های پروژه (مسیرها را مطابق پروژه خود چک کنید)
from main_api.core.database import get_db
from main_api.modules.auth.dependencies import get_current_user

from .schemas import TelemetryReportResponse, AggregatedReportResponse
from .service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/feeder/{feeder_id}", response_model=List[TelemetryReportResponse])
async def get_feeder_report(
    feeder_id: int,
    start_date: datetime = Query(..., description="مثال: 2024-01-01T00:00:00"),
    end_date: datetime = Query(..., description="مثال: 2024-01-31T23:59:59"),
    db: AsyncSession = Depends(get_db)
):
    """دریافت تاریخچه تمام دیتاهای ثبت شده برای یک فیدر مشخص در بازه زمانی"""
    try:
        service = ReportService(db)
        data = await service.fetch_feeder_report(feeder_id, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/feeder/{feeder_id}", response_model=AggregatedReportResponse)
async def get_feeder_analytics(
    feeder_id: int,
    parameter_key: str = Query(..., description="مثلاً active_power یا voltage"),
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """دریافت گزارش آماری (میانگین، بیشترین و کمترین) برای یک پارامتر خاص از فیدر"""
    try:
        service = ReportService(db)
        return await service.fetch_aggregated_report(feeder_id, parameter_key, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
