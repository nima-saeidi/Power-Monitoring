from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from modules.schemas import (
    LogFilterRequest,
    LogListResponse,
    LogItem,
    LogFilterOptionsResponse,
    LogPurgeResponse,
)
from modules.services import logging_service_instance

router = APIRouter(prefix="/logs", tags=["Logs & Audits"])


@router.get("", response_model=LogListResponse)
async def fetch_logs(
    service_name: Optional[str] = Query(default=None, description="Filter by service name (e.g. main_api)"),
    action: Optional[str] = Query(default=None, description="Filter by action name"),
    user_id: Optional[int] = Query(default=None, description="Filter by User ID"),
    search: Optional[str] = Query(default=None, description="Search keyword in action/service"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (INFO/WARNING/ERROR/CRITICAL)"),
    success: Optional[bool] = Query(default=None, description="Filter by success flag"),
    start_date: Optional[datetime] = Query(default=None, description="Filter logs created at/after this time"),
    end_date: Optional[datetime] = Query(default=None, description="Filter logs created at/before this time"),
    limit: int = Query(default=50, ge=1, le=1000, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset")
):
    """دریافت لاگ‌ها از دیتابیس PostgreSQL با امکان فیلتر و صفحه‌بندی"""
    try:
        filters = LogFilterRequest(
            service_name=service_name,
            action=action,
            user_id=user_id,
            search=search,
            severity=severity,
            success=success,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return await logging_service_instance.get_logs(filters)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching logs from database: {str(e)}"
        )


@router.get("/meta/filters", response_model=LogFilterOptionsResponse)
async def fetch_filter_options():
    """لیست مقادیر یکتای service_name/action برای ساخت فیلترهای پنل ادمین"""
    return await logging_service_instance.get_filter_options()


@router.delete("", response_model=LogPurgeResponse)
async def purge_logs(
    older_than_days: int = Query(default=90, ge=1, le=3650, description="حذف لاگ‌های قدیمی‌تر از این تعداد روز")
):
    """حذف لاگ‌های قدیمی‌تر از تعداد روز مشخص شده"""
    deleted_count = await logging_service_instance.purge_old_logs(older_than_days)
    return LogPurgeResponse(deleted_count=deleted_count)


@router.get("/{log_id}", response_model=LogItem)
async def fetch_log_by_id(log_id: int):
    """دریافت یک رکورد لاگ مشخص با شناسه"""
    log = await logging_service_instance.get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return log
