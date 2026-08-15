from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil

from core.database import get_db
from core.auth import get_current_user, require_role
from modules.users.models import User
from modules.audit_logs.repository import AuditLogRepository, CommandLogRepository
from modules.audit_logs.schemas import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogFilterParams,
    CommandLogResponse,
    CommandLogListResponse,
    CommandLogFilterParams,
    UserActivityResponse
)
from core.logging import api_logger


router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=AuditLogListResponse)
async def get_audit_logs(
    user_id: Optional[int] = Query(None, description="فیلتر بر اساس کاربر"),
    action: Optional[str] = Query(None, description="فیلتر بر اساس نوع عملیات"),
    resource_type: Optional[str] = Query(None, description="فیلتر بر اساس نوع منبع"),
    severity: Optional[str] = Query(None, pattern="^(debug|info|warning|error|critical)$"),
    success: Optional[bool] = Query(None, description="فیلتر بر اساس موفقیت"),
    start_date: Optional[datetime] = Query(None, description="تاریخ شروع"),
    end_date: Optional[datetime] = Query(None, description="تاریخ پایان"),
    page: int = Query(1, ge=1, description="شماره صفحه"),
    page_size: int = Query(50, ge=1, le=100, description="تعداد آیتم در صفحه"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """دریافت لیست لاگ‌های ممیزی با فیلترها"""
    
    skip = (page - 1) * page_size
    
    logs, total = await AuditLogRepository.get_logs(
        db=db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        severity=severity,
        success=success,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=page_size
    )
    
    pages = ceil(total / page_size) if total > 0 else 0
    
    api_logger.info(
        f"User {current_user.username} retrieved {len(logs)} audit logs "
        f"(page {page}/{pages}, total {total})"
    )
    
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/search", response_model=AuditLogListResponse)
async def search_audit_logs(
    q: str = Query(..., min_length=1, description="عبارت جستجو"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """جستجو در لاگ‌های ممیزی"""
    
    skip = (page - 1) * page_size
    
    logs, total = await AuditLogRepository.search_logs(
        db=db,
        search_term=q,
        skip=skip,
        limit=page_size
    )
    
    pages = ceil(total / page_size) if total > 0 else 0
    
    api_logger.info(
        f"User {current_user.username} searched audit logs with query '{q}', "
        f"found {total} results"
    )
    
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """دریافت یک لاگ ممیزی خاص"""
    
    log = await AuditLogRepository.get_by_id(db, log_id)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with id {log_id} not found"
        )
    
    return AuditLogResponse.model_validate(log)


@router.get("/user/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: int,
    days: int = Query(30, ge=1, le=365, description="تعداد روزها"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """دریافت فعالیت‌های اخیر یک کاربر"""
    
    # Check if target user exists
    from modules.users.repository import UserRepository
    target_user = await UserRepository.get_by_id(db, user_id)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    logs = await AuditLogRepository.get_user_activity(db, user_id, days)
    
    total_actions = len(logs)
    successful_actions = sum(1 for log in logs if log.success)
    failed_actions = total_actions - successful_actions
    
    api_logger.info(
        f"User {current_user.username} retrieved activity for user {target_user.username} "
        f"({total_actions} actions in last {days} days)"
    )
    
    return UserActivityResponse(
        user_id=user_id,
        username=target_user.username,
        total_actions=total_actions,
        successful_actions=successful_actions,
        failed_actions=failed_actions,
        recent_logs=[AuditLogResponse.model_validate(log) for log in logs[:50]],
        period_days=days
    )


@router.get("/failed/recent", response_model=AuditLogListResponse)
async def get_failed_operations(
    hours: int = Query(24, ge=1, le=168, description="تعداد ساعات"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """دریافت عملیات‌های ناموفق اخیر"""
    
    logs = await AuditLogRepository.get_failed_operations(db, hours)
    
    api_logger.warning(
        f"User {current_user.username} retrieved {len(logs)} failed operations "
        f"from last {hours} hours"
    )
    
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
        pages=1
    )


@router.delete("/purge", status_code=status.HTTP_200_OK)
async def purge_old_logs(
    days: int = Query(90, ge=30, le=365, description="حذف لاگ‌های قدیمی‌تر از این روز"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """حذف لاگ‌های ممیزی قدیمی (تنها برای مدیر ارشد)"""
    
    deleted_count = await AuditLogRepository.delete_old_logs(db, days)

    # ثبت عملیات حذف در لاگ ممیزی جدید
    await AuditLogRepository.create(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        user_role=current_user.role,
        action="PURGE_AUDIT_LOGS",
        resource_type="system",
        description=f"Purged {deleted_count} logs older than {days} days.",
        severity="warning"
    )

    return {
        "success": True,
        "message": f"Successfully deleted {deleted_count} old audit logs.",
        "deleted_count": deleted_count
    }


# ==========================================
# Command Logs Router
# ==========================================
command_router = APIRouter(prefix="/command-logs", tags=["Command Logs"])

@command_router.get("/", response_model=CommandLogListResponse)
async def get_command_logs(
    post_id: Optional[int] = Query(None, description="شناسه پست"),
    feeder_id: Optional[int] = Query(None, description="شناسه فیدر"),
    user_id: Optional[int] = Query(None, description="شناسه کاربر"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """دریافت لیست دستورات Modbus"""
    
    skip = (page - 1) * page_size
    
    logs, total = await CommandLogRepository.get_command_history(
        db=db,
        post_id=post_id,
        feeder_id=feeder_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=page_size
    )
    
    pages = ceil(total / page_size) if total > 0 else 0
    
    api_logger.info(
        f"User {current_user.username} retrieved {len(logs)} command logs "
        f"(page {page}/{pages})"
    )
    
    return CommandLogListResponse(
        items=[CommandLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@command_router.get("/failed", response_model=CommandLogListResponse)
async def get_failed_commands(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    """لیست دستورات Modbus که خطا داشته‌اند"""
    
    logs = await CommandLogRepository.get_failed_commands(db, hours)
    
    return CommandLogListResponse(
        items=[CommandLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
        pages=1
    )