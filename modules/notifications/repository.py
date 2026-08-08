from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

# فرض بر این است که این ماژول‌ها در پروژه شما وجود دارند
from modules.notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationPreference,
    NotificationType,
    NotificationPriority
)
from core.logging import api_logger


class NotificationRepository:
    """Repository برای مدیریت نوتیفیکیشن‌ها"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        source_type: Optional[str] = None,
        source_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """ایجاد نوتیفیکیشن جدید"""
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            priority=priority,
            source_type=source_type,
            source_id=source_id,
            metadata=metadata,
            action_url=action_url,
            expires_at=expires_at
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        api_logger.info(
            f"Created notification {notification.id} for user {user_id}: "
            f"{type.value} - {title}"
        )
        
        return notification
    
    @staticmethod
    async def get_by_id(db: AsyncSession, notification_id: int) -> Optional[Notification]:
        """دریافت نوتیفیکیشن با ID"""
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        include_dismissed: bool = False,
        type_filter: Optional[NotificationType] = None,
        priority_filter: Optional[NotificationPriority] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Notification], int]:
        """دریافت نوتیفیکیشن‌های یک کاربر"""
        
        query = select(Notification).where(Notification.user_id == user_id)
        
        # فیلترها
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        if not include_dismissed:
            query = query.where(Notification.is_dismissed == False)
        
        if type_filter:
            query = query.where(Notification.type == type_filter)
        
        if priority_filter:
            query = query.where(Notification.priority == priority_filter)
        
        # حذف نوتیفیکیشن‌های منقضی شده
        query = query.where(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )
        
        # شمارش کل
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # مرتب‌سازی و صفحه‌بندی
        query = query.order_by(desc(Notification.created_at))
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return list(notifications), total
    
    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """علامت‌گذاری نوتیفیکیشن به عنوان خوانده شده"""
        
        query = select(Notification).where(Notification.id == notification_id)
        
        if user_id:
            query = query.where(Notification.user_id == user_id)
        
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        await db.commit()
        return True
    
    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
        """علامت‌گذاری همه نوتیفیکیشن‌های کاربر به عنوان خوانده شده"""
        
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )

        notifications = result.scalars().all()

        for n in notifications:
            n.is_read = True
            n.read_at = datetime.utcnow()

        await db.commit()

        return len(notifications)

    @staticmethod
    async def dismiss(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        """نادیده گرفتن نوتیفیکیشن"""
        
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )

        notification = result.scalar_one_or_none()

        if not notification:
            return False

        notification.is_dismissed = True
        notification.dismissed_at = datetime.utcnow()

        await db.commit()

        return True

    @staticmethod
    async def get_preferences(db: AsyncSession, user_id: int) -> NotificationPreference:
        """دریافت تنظیمات نوتیفیکیشن کاربر"""
        
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )

        pref = result.scalar_one_or_none()

        if not pref:
            # ایجاد تنظیمات پیش‌فرض در صورت نبودن
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
            await db.commit()
            await db.refresh(pref)

        return pref
