# app/reports/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession  # <--- تغییر به AsyncSession
from typing import List, Optional
from datetime import datetime

# ایمپورت‌های کلی پروژه
from main_api.core.database import get_db
from main_api.modules.auth.dependencies import get_current_user

# ایمپورت از مدل‌های محلی این ماژول
from .schemas import (
    TelemetryReportResponse,
    AggregatedReportResponse,
    AlertReportResponse,
    PostStatusResponse
)
from .service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/feeder/{feeder_id}", response_model=List[TelemetryReportResponse])
async def get_feeder_report(  # <--- نام تابع و ساختار روتر اصلاح شد
    feeder_id: int,
    start_date: datetime = Query(..., description="مثال: 2024-01-01T00:00:00"),
    end_date: datetime = Query(..., description="مثال: 2024-01-31T23:59:59"),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ReportService(db)
        data = await service.fetch_feeder_report(feeder_id, start_date, end_date)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/feeder/{feeder_id}", response_model=AggregatedReportResponse)
async def get_feeder_analytics(  # <--- async اضافه شد
        feeder_id: int,
        parameter_key: str = Query(..., description="مثلاً voltage_a یا active_power"),
        start_date: datetime = Query(...),
        end_date: datetime = Query(...),
        db: AsyncSession = Depends(get_db)  # <--- تغییر به AsyncSession
):
    try:
        service = ReportService(db)
        return await service.fetch_aggregated_report(feeder_id, parameter_key, start_date, end_date) # <--- await اضافه شد
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/alerts", response_model=List[AlertReportResponse])
async def get_alerts_report(  # <--- async اضافه شد
        start_date: datetime = Query(...),
        end_date: datetime = Query(...),
        post_id: Optional[int] = Query(None, description="فیلتر بر اساس پست خاص (اختیاری)"),
        db: AsyncSession = Depends(get_db)  # <--- تغییر به AsyncSession
):
    try:
        service = ReportService(db)
        return await service.fetch_alerts_report(start_date, end_date, post_id) # <--- await اضافه شد
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard/posts-status", response_model=List[PostStatusResponse])
async def get_dashboard_status(db: AsyncSession = Depends(get_db)):  # <--- async و AsyncSession
    service = ReportService(db)
    posts = await service.fetch_posts_dashboard_status() # <--- await اضافه شد

    results = []
    for p in posts:
        results.append({
            "post_id": p.id,
            "post_name": p.name,
            "status": "normal",  # این وضعیت می‌تواند بر اساس Redis یا Alert ها داینامیک شود
            "last_update": datetime.now()
        })
    return results
