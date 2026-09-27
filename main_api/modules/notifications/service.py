import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from main_api.modules.notifications.repository import NotificationRepository
from main_api.modules.notifications.websocket import notifier_manager
from main_api.modules.notifications.models import (
    NotificationType,
    NotificationPriority,
    NotificationPreference
)
from main_api.core.logging import api_logger
from main_api.modules.notifications.schemas import (
    NotificationCreateRequest,
    NotificationBulkCreateRequest,
    NotificationResponse,
)

from main_api.modules.audit_logs.services import send_audit_log

try:
    from main_api.core.rabbitmq_publisher import send_notification as send_rabbitmq_notification
    from main_api.schemas.notification import NotificationPayload
except ImportError:
    send_rabbitmq_notification = None
    NotificationPayload = None


class NotificationService:

    @staticmethod
    async def send_notification(
            db: AsyncSession,
            request: NotificationCreateRequest,
            background_tasks: Optional[BackgroundTasks] = None,
            username: Optional[str] = None
    ):

        preferences = await NotificationRepository.get_preferences(db, request.user_id)

        if not NotificationService._should_send(preferences, request.type, request.priority):
            api_logger.info(f"Notification for user {request.user_id} blocked by preferences.")

            log_coroutine = send_audit_log(
                action="NOTIFICATION_BLOCKED", username=username, success=False, severity="INFO",
                description=f"نوتیفیکیشن '{request.title}' برای کاربر {request.user_id} بر اساس تنظیمات شخصی مسدود شد."
            )
            if background_tasks:
                background_tasks.add_task(lambda: asyncio.create_task(log_coroutine))
            else:
                asyncio.create_task(log_coroutine)

            return None

        notification = await NotificationRepository.create(db=db, **request.dict())
        await NotificationService._push_live(notification)

        log_coroutine = send_audit_log(
            action="SEND_NOTIFICATION", username=username, success=True, severity="INFO",
            description=f"نوتیفیکیشن '{notification.title}' برای کاربر {notification.user_id} با موفقیت در دیتابیس ثبت شد."
        )
        if background_tasks:
            background_tasks.add_task(lambda: asyncio.create_task(log_coroutine))
        else:
            asyncio.create_task(log_coroutine)

        return notification

    @staticmethod
    async def send_bulk_notification(
            db: AsyncSession,
            request: NotificationBulkCreateRequest,
            background_tasks: Optional[BackgroundTasks] = None,
            username: Optional[str] = None
    ) -> Dict[str, Any]:
        sent_count, blocked_count = 0, 0

        for user_id in request.user_ids:
            preferences = await NotificationRepository.get_preferences(db, user_id)
            if not NotificationService._should_send(preferences, request.type, request.priority):
                blocked_count += 1
                continue

            notification = await NotificationRepository.create(
                db=db, user_id=user_id, **request.dict(exclude={'user_ids'})
            )
            await NotificationService._push_live(notification)
            sent_count += 1

        log_coroutine = send_audit_log(
            action="SEND_BULK_NOTIFICATION", username=username, success=True, severity="INFO",
            description=(f"ارسال گروهی نوتیفیکیشن '{request.title}': "
                         f"{sent_count} ارسال موفق، {blocked_count} مسدود شده از مجموع {len(request.user_ids)} کاربر.")
        )
        if background_tasks:
            background_tasks.add_task(lambda: asyncio.create_task(log_coroutine))
        else:
            asyncio.create_task(log_coroutine)

        return {"sent": sent_count, "blocked": blocked_count, "total": len(request.user_ids)}

    @staticmethod
    async def send_system_alert(
            db: AsyncSession,
            user_id: int,
            title: str, message: str, source_type: str, source_id: int,
            priority: NotificationPriority = NotificationPriority.HIGH,
            action_url: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            background_tasks: Optional[BackgroundTasks] = None,
            username: Optional[str] = "System"
    ):
        request = NotificationCreateRequest(
            user_id=user_id, title=title, message=message, type=NotificationType.ALERT,
            priority=priority, source_type=source_type, source_id=source_id,
            action_url=action_url, metadata=metadata
        )

        log_coroutine = send_audit_log(
            action="SYSTEM_ALERT_ISSUED", username=username, success=True, severity="WARNING",
            description=f"هشدار سیستمی با عنوان '{title}' برای کاربر {user_id} صادر شد."
        )
        if background_tasks:
            background_tasks.add_task(lambda: asyncio.create_task(log_coroutine))
        else:
            asyncio.create_task(log_coroutine)

        return await NotificationService.send_notification(db, request, background_tasks, username)

    @staticmethod
    async def notify_power_outage(
            db: AsyncSession, user_ids: List[int], post_name: str, post_id: int,
            background_tasks: BackgroundTasks,
            feeder_name: Optional[str] = None,
            username: Optional[str] = "System"
    ):
        title = f"قطعی برق - {post_name}" + (f" / {feeder_name}" if feeder_name else "")
        message = f"پست {post_name}" + (f" و فیدر {feeder_name}" if feeder_name else "") + " دچار قطعی برق شده است."

        background_tasks.add_task(
            send_audit_log, action="POWER_OUTAGE_ALERT", username=username, success=True, severity="CRITICAL",
            description=f"قطعی برق شناسایی شد: پست '{post_name}'" + (f", فیدر '{feeder_name}'." if feeder_name else ".")
        )

        request = NotificationBulkCreateRequest(
            user_ids=user_ids, title=title, message=message, type=NotificationType.ALERT,
            priority=NotificationPriority.CRITICAL, source_type="post", source_id=post_id,
            action_url=f"/monitoring/posts/{post_id}",
            metadata={"post_name": post_name, "feeder_name": feeder_name, "event_type": "power_outage"}
        )
        await NotificationService.send_bulk_notification(db, request, background_tasks, username)

        if send_rabbitmq_notification and NotificationPayload:
            payload = NotificationPayload(provider="sms", recipient="managers_group", message=message)
            background_tasks.add_task(send_rabbitmq_notification, payload)

        return {"status": "Critical power outage alert processed and logged"}

    @staticmethod
    async def notify_threshold_exceeded(
            db: AsyncSession, user_ids: List[int], post_name: str, post_id: int,
            parameter_name: str, current_value: float, threshold: float,
            background_tasks: BackgroundTasks, unit: str = "",
            username: Optional[str] = "System"
    ):
        title = f"هشدار ⚠️: {parameter_name} غیرمجاز"
        message = (f"در پست {post_name}، مقدار {parameter_name} به {current_value}{unit} "
                   f"رسیده که از حد مجاز ({threshold}{unit}) فراتر است.")

        background_tasks.add_task(
            send_audit_log, action="THRESHOLD_EXCEEDED_ALERT", username=username, success=True, severity="WARNING",
            description=f"هشدار عبور از آستانه برای {parameter_name} در پست '{post_name}': مقدار فعلی {current_value}, حد مجاز {threshold}."
        )

        request = NotificationBulkCreateRequest(
            user_ids=user_ids, title=title, message=message, type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH, source_type="post", source_id=post_id,
            action_url=f"/monitoring/posts/{post_id}",
            metadata={"post_name": post_name, "parameter": parameter_name, "value": current_value,
                      "threshold": threshold}
        )
        await NotificationService.send_bulk_notification(db, request, background_tasks, username)

        if send_rabbitmq_notification and NotificationPayload:
            payload = NotificationPayload(provider="sms", recipient="technical_team", message=message)
            background_tasks.add_task(send_rabbitmq_notification, payload)

        return {"status": "Threshold violation alert processed and logged"}

    @staticmethod
    async def _push_live(notification) -> None:
        payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
        await notifier_manager.send_personal_message(
            {"type": "NEW_NOTIFICATION", "data": payload}, notification.user_id
        )

    @staticmethod
    def _should_send(pref: NotificationPreference, n_type: NotificationType, priority: NotificationPriority) -> bool:
        if not pref: return True
        type_mapping = {
            NotificationType.INFO: pref.enable_info, NotificationType.WARNING: pref.enable_warning,
            NotificationType.ERROR: pref.enable_error, NotificationType.SUCCESS: pref.enable_success,
            NotificationType.ALERT: pref.enable_alert
        }
        priority_levels = {
            NotificationPriority.LOW: 0, NotificationPriority.MEDIUM: 1,
            NotificationPriority.HIGH: 2, NotificationPriority.CRITICAL: 3
        }
        if not type_mapping.get(n_type, True): return False
        if priority_levels.get(priority, 0) < priority_levels.get(pref.min_priority, 0): return False
        return True
