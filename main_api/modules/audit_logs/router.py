from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status

from main_api.modules.auth.dependencies import require_admin, require_tech_or_admin
from main_api.modules.auth.models import User
from main_api.modules.audit_logs.schemas import (
    AuditLogResponse, AuditLogListResponse, CommandLogListResponse,
    UserActivityResponse, DeviceTestLogListResponse
)

# ایمپورت کردن وابستگی‌های سرویس که در مرحله قبل ساختیم
from main_api.modules.audit_logs.dependencies import (
    get_audit_log_service,
    get_command_log_service,
    get_device_test_log_service
)
from main_api.modules.audit_logs.services import (
    AuditLogService, CommandLogService, DeviceTestLogService
)

# ==========================================
# Audit Logs Router
# ==========================================
router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
        user_id: Optional[int] = Query(None, description="فیلتر بر اساس کاربر"),
        action: Optional[str] = Query(None, description="فیلتر بر اساس نوع عملیات"),
        service_name: Optional[str] = Query(None, description="فیلتر بر اساس نام سرویس (main_api, notification_service, ...)"),
        severity: Optional[str] = Query(None, pattern="^(?i)(debug|info|warning|error|critical)$"),
        success: Optional[bool] = Query(None, description="فیلتر بر اساس موفقیت"),
        start_date: Optional[datetime] = Query(None, description="تاریخ شروع"),
        end_date: Optional[datetime] = Query(None, description="تاریخ پایان"),
        page: int = Query(1, ge=1, description="شماره صفحه"),
        page_size: int = Query(50, ge=1, le=100, description="تعداد آیتم در صفحه"),
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_logs(
        user_id, action, service_name, severity, success,
        start_date, end_date, page, page_size
    )


@router.get("/meta/filters")
async def get_audit_log_filters(
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    """لیست مقادیر یکتای سرویس‌ها و اکشن‌ها برای ساخت کشوی فیلتر در پنل ادمین"""
    return await service.get_filter_options()


@router.get("/search", response_model=AuditLogListResponse)
async def search_audit_logs(
        q: str = Query(..., min_length=1, description="عبارت جستجو"),
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.search_logs(q, page, page_size)


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
        log_id: int,
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_log_by_id(log_id)


@router.get("/user/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
        user_id: int,
        days: int = Query(30, ge=1, le=365, description="تعداد روزها"),
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_user_activity(user_id, days)


@router.delete("/purge", status_code=status.HTTP_200_OK)
async def purge_old_logs(
        days: int = Query(90, ge=30, le=365, description="حذف لاگ‌های قدیمی‌تر از این روز"),
        service: AuditLogService = Depends(get_audit_log_service),
        current_user: User = Depends(require_admin)
):
    return await service.purge_old_logs(days, current_user)


# ==========================================
# Command Logs Router
# ==========================================
command_router = APIRouter(prefix="/command-logs", tags=["Command Logs"])

@command_router.get("/", response_model=CommandLogListResponse)
async def get_command_logs(
        post_id: Optional[int] = Query(None),
        feeder_id: Optional[int] = Query(None),
        user_id: Optional[int] = Query(None),
        start_date: Optional[datetime] = Query(None),
        end_date: Optional[datetime] = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        service: CommandLogService = Depends(get_command_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_command_logs(
        post_id, feeder_id, user_id, start_date, end_date, page, page_size
    )


@command_router.get("/failed", response_model=CommandLogListResponse)
async def get_failed_commands(
        hours: int = Query(24, ge=1, le=168),
        service: CommandLogService = Depends(get_command_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_failed_commands(hours)


# ==========================================
# Device Test Logs Router
# ==========================================
test_log_router = APIRouter(prefix="/test-logs", tags=["Device Test Logs"])

@test_log_router.get("/", response_model=DeviceTestLogListResponse)
async def get_recent_test_logs(
        limit: int = Query(50, ge=1, le=200),
        service: DeviceTestLogService = Depends(get_device_test_log_service),
        current_user: User = Depends(require_tech_or_admin)
):
    return await service.get_recent_tests(limit)
