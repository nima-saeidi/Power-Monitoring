# app/reports/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from typing import Optional
from app.reports.schemas import AggregatedReportResponse, AlertReportResponse, PostStatusResponse
from app.database import get_db
from app.auth.dependencies import get_current_user # همان متدی که در تصویر در پوشه auth دارید

from app.reports.schemas import TelemetryReportResponse
from app.reports.service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)] # تمام روت‌های این فایل نیاز به توکن دارند
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


# ۲. دریافت گزارش هشدارها (عملیاتی)
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


# ۳. دریافت وضعیت کلی پست‌ها برای داشبورد
@router.get("/dashboard/posts-status")
def get_dashboard_status(db: Session = Depends(get_db)):
    # نکته: معمولاً برای داشبورد از مدل دقیق‌تری استفاده می‌شود. اینجا ساختار اولیه ارائه شده است.
    service = ReportService(db)
    posts = service.fetch_posts_dashboard_status()

    # ساختن پاسخ موقت - بهتر است این بخش با وضعیت واقعی (خوانده شده از کش/ردیس) ترکیب شود
    results = []
    for p in posts:
        results.append({
            "post_id": p.id,
            "post_name": p.name,
            "status": "normal",  # این بخش در آینده بر اساس آلارم‌های فعال تغییر می‌کند
            "last_update": datetime.now()
        })
    return results