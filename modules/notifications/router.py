from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from core.security import get_current_user
from modules.auth.models import User
from modules.notifications.schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationMarkReadRequest,
    NotificationPreferenceUpdateRequest,
    NotificationFilterParams
)
from modules.notifications.repository import NotificationRepository
from modules.notifications.service import NotificationService
from modules.notifications.models import NotificationPreference


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    params: NotificationFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """دریافت لیست نوتیفیکیشن‌های کاربر"""
    
    notifications, total = await NotificationRepository.get_user_notifications(
        db,
        user_id=current_user.id,
        unread_only=params.unread_only,
        include_dismissed=params.include_dismissed,
        type_filter=params.type,
        priority_filter=params.priority,
        skip=(params.page - 1) * params.page_size,
        limit=params.page_size
    )
    
    # شمارش تعداد خوانده نشده برای نمایش در UI
    unread_count_query = await NotificationRepository.get_user_notifications(
        db, user_id=current_user.id, unread_only=True
    )
    unread_count = unread_count_query[1]
    
    return {
        "items": notifications,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "unread_count": unread_count
    }


@router.post("/read")
async def mark_notifications_as_read(
    request: NotificationMarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """علامت‌گذاری نوتیفیکیشن‌ها به عنوان خوانده شده"""
    
    for n_id in request.notification_ids:
        await NotificationRepository.mark_as_read(db, n_id, current_user.id)
        
    return {"message": "Success"}


@router.post("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """علامت‌گذاری همه به عنوان خوانده شده"""
    
    count = await NotificationRepository.mark_all_as_read(db, current_user.id)
    return {"message": f"{count} notifications marked as read"}


@router.post("/dismiss/{notification_id}")
async def dismiss_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """نادیده گرفتن یک نوتیفیکیشن"""
    
    success = await NotificationRepository.dismiss(db, notification_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    return {"message": "Notification dismissed"}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """دریافت تنظیمات نوتیفیکیشن"""
    return await NotificationRepository.get_preferences(db, current_user.id)


@router.put("/preferences")
async def update_preferences(
    request: NotificationPreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """به‌روزرسانی تنظیمات نوتیفیکیشن"""
    
    pref = await NotificationRepository.get_preferences(db, current_user.id)
    
    for field, value in request.dict(exclude_unset=True).items():
        setattr(pref, field, value)
        
    await db.commit()
    await db.refresh(pref)
    
    return pref
