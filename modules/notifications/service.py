from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from modules.notifications.models import NotificationType, NotificationPriority
from modules.notifications.repository import NotificationRepository
from modules.notifications.models import (
    NotificationType,
    NotificationPriority,

    NotificationPreference  # این مورد اضافه شد
)

from core.logging import api_logger
from modules.notifications.schemas import (
    NotificationCreateRequest,
    NotificationBulkCreateRequest,
    NotificationResponse,

)

class NotificationService:
    """سرویس مدیریت نوتیفیکیشن‌ها"""
    
    @staticmethod
    async def send_notification(
        db: AsyncSession,
        request: NotificationCreateRequest
    ):
        """ارسال نوتیفیکیشن به یک کاربر"""
        
        # بررسی تنظیمات کاربر
        preferences = await NotificationRepository.get_preferences(db, request.user_id)
        
        # بررسی فیلترهای کاربر
        if not NotificationService._should_send(preferences, request.type, request.priority):
            api_logger.info(
                f"Notification blocked by user preferences: "
                f"user={request.user_id}, type={request.type}, priority={request.priority}"
            )
            return None
        
        # ایجاد نوتیفیکیشن
        notification = await NotificationRepository.create(
            db=db,
            user_id=request.user_id,
            title=request.title,
            message=request.message,
            type=request.type,
            priority=request.priority,
            source_type=request.source_type,
            source_id=request.source_id,
            metadata=request.metadata,
            action_url=request.action_url,
            expires_at=request.expires_at
        )
        
        return notification
    
    @staticmethod
    async def send_bulk_notification(
        db: AsyncSession,
        request: NotificationBulkCreateRequest
    ) -> Dict[str, Any]:
        """ارسال نوتیفیکیشن به چند کاربر"""
        
        sent_count = 0
        blocked_count = 0
        
        for user_id in request.user_ids:
            # بررسی تنظیمات هر کاربر
            preferences = await NotificationRepository.get_preferences(db, user_id)
            
            if not NotificationService._should_send(preferences, request.type, request.priority):
                blocked_count += 1
                continue
            
            # ایجاد نوتیفیکیشن
            await NotificationRepository.create(
                db=db,
                user_id=user_id,
                title=request.title,
                message=request.message,
                type=request.type,
                priority=request.priority,
                source_type=request.source_type,
                source_id=request.source_id,
                metadata=request.metadata,
                action_url=request.action_url,
                expires_at=request.expires_at
            )
            sent_count += 1
        
        api_logger.info(
            f"Bulk notification sent: {sent_count} sent, {blocked_count} blocked"
        )
        
        return {
            "sent": sent_count,
            "blocked": blocked_count,
            "total": len(request.user_ids)
        }
    
    @staticmethod
    async def send_system_alert(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        source_type: str,
        source_id: int,
        priority: NotificationPriority = NotificationPriority.HIGH,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """ارسال هشدار سیستمی (برای مانیتورینگ پست‌ها)"""
        
        request = NotificationCreateRequest(
            user_id=user_id,
            title=title,
            message=message,
            type=NotificationType.ALERT,
            priority=priority,
            source_type=source_type,
            source_id=source_id,
            action_url=action_url,
            metadata=metadata
        )
        
        return await NotificationService.send_notification(db, request)
    
    @staticmethod
    async def notify_power_outage(
        db: AsyncSession,
        user_ids: List[int],
        post_name: str,
        post_id: int,
        feeder_name: Optional[str] = None
    ):
        """نوتیفیکیشن قطعی برق"""
        
        if feeder_name:
            title = f"قطعی برق - {post_name} / {feeder_name}"
            message = f"فیدر {feeder_name} در پست {post_name} قطع شده است."
        else:
            title = f"قطعی برق - {post_name}"
            message = f"پست {post_name} دچار قطعی برق شده است."
        
        request = NotificationBulkCreateRequest(
            user_ids=user_ids,
            title=title,
            message=message,
            type=NotificationType.ALERT,
            priority=NotificationPriority.CRITICAL,
            source_type="post",
            source_id=post_id,
            action_url=f"/monitoring/posts/{post_id}",
            metadata={
                "post_name": post_name,
                "feeder_name": feeder_name,
                "event_type": "power_outage"
            }
        )
        
        return await NotificationService.send_bulk_notification(db, request)
    
    @staticmethod
    async def notify_threshold_exceeded(
        db: AsyncSession,
        user_ids: List[int],
        post_name: str,
        post_id: int,
        parameter_name: str,
        current_value: float,
        threshold: float,
        unit: str = ""
    ):
        """نوتیفیکیشن عبور از آستانه"""
        
        title = f"هشدار ⚠️: {parameter_name} غیرمجاز"
        message = (
            f"در پست {post_name}، مقدار {parameter_name} به {current_value}{unit} "
            f"رسیده است که از حد آستانه ({threshold}{unit}) فراتر رفته است."
        )
        
        request = NotificationBulkCreateRequest(
            user_ids=user_ids,
            title=title,
            message=message,
            type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH,
            source_type="post",
            source_id=post_id,
            action_url=f"/monitoring/posts/{post_id}",
            metadata={
                "post_name": post_name,
                "parameter_name": parameter_name,
                "value": current_value,
                "threshold": threshold,
                "event_type": "threshold_exceeded"
            }
        )
        
        return await NotificationService.send_bulk_notification(db, request)

    @staticmethod
    def _should_send(
        pref: NotificationPreference,
        n_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """بررسی اینکه آیا نوتیفیکیشن باید ارسال شود یا خیر (بر اساس تنظیمات کاربر)"""
        
        # بررسی فعال بودن نوع نوتیفیکیشن
        type_mapping = {
            NotificationType.INFO: pref.enable_info,
            NotificationType.WARNING: pref.enable_warning,
            NotificationType.ERROR: pref.enable_error,
            NotificationType.SUCCESS: pref.enable_success,
            NotificationType.ALERT: pref.enable_alert
        }
        
        if not type_mapping.get(n_type, True):
            return False
            
        # بررسی اولویت
        priority_levels = {
            NotificationPriority.LOW: 0,
            NotificationPriority.MEDIUM: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.CRITICAL: 3
        }
        
        if priority_levels.get(priority, 0) < priority_levels.get(pref.min_priority, 0):
            return False
            
        return True
