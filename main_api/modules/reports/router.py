# app/reports/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
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
def get_feeder_report(
    feeder_id: int,
    start_date: datetime = Query(..., description="مثال: 2024-01-01T00:00:00"),
    end_date: datetime = Query(..., description="مثال: 2024-01-31T23:59:59"),
    db: Session = Depends(get_db)
):
    try:
        service = ReportService(db)
        data = service.fetch_feeder_report(feeder_id, start_date, end_date)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="خطای سرور در پردازش گزارش")

@router.get("/analytics/feeder/{feeder_id}", response_model=AggregatedReportResponse)
def get_feeder_analytics(
        feeder_id: int,
        parameter_key: str = Query(..., description="مثلاً voltage_a یا active_power"),
        start_date: datetime = Query(...),
        end_date: datetime = Query(...),
        db: Session = Depends(get_db)
):
    try:
        service = ReportService(db)
        return service.fetch_aggregated_report(feeder_id, parameter_key, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/alerts", response_model=List[AlertReportResponse])
def get_alerts_report(
        start_date: datetime = Query(...),
        end_date: datetime = Query(...),
        post_id: Optional[int] = Query(None, description="فیلتر بر اساس پست خاص (اختیاری)"),
        db: Session = Depends(get_db)
):
    try:
        service = ReportService(db)
        return service.fetch_alerts_report(start_date, end_date, post_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard/posts-status", response_model=List[PostStatusResponse])
def get_dashboard_status(db: Session = Depends(get_db)):
    service = ReportService(db)
    posts = service.fetch_posts_dashboard_status()

    results = []
    for p in posts:
        results.append({
            "post_id": p.id,
            "post_name": p.name,
            "status": "normal",  # این وضعیت می‌تواند بر اساس Redis یا Alert ها داینامیک شود
            "last_update": datetime.now()
        })
    return results
