import asyncio
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.broker import send_notification_to_queue
from main_api.modules.audit_logs.services import send_audit_log
from main_api.modules.notifications.models import NotificationPriority, NotificationType
from main_api.modules.notifications.schemas import NotificationBulkCreateRequest
from main_api.modules.notifications.service import NotificationService
from main_api.modules.users.repository import UserRepository


async def dispatch_alert(
        db: AsyncSession,
        *,
        title: str,
        message: str,
        n_type: NotificationType,
        priority: NotificationPriority,
        source_type: str,
        source_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        email_html: Optional[str] = None,
) -> None:
    user_repo = UserRepository(db)
    try:
        user_ids = [u.id for u in await user_repo.get_all() if u.is_active]
        if user_ids:
            await NotificationService.send_bulk_notification(
                db,
                NotificationBulkCreateRequest(
                    user_ids=user_ids, title=title, message=message, type=n_type, priority=priority,
                    source_type=source_type, source_id=source_id, metadata=metadata,
                ),
                username="System",
            )

        if email_html:
            emails = await user_repo.get_notification_enabled_emails()
            if emails:
                await send_notification_to_queue(
                    title=title,
                    message=message,
                    html_message=email_html,
                    channel="email",
                    email_addresses=emails,
                    priority="high" if priority in (NotificationPriority.HIGH, NotificationPriority.CRITICAL) else "normal",
                    metadata=metadata,
                )
    except Exception as e:
        asyncio.create_task(send_audit_log(
            action="ALERT_DISPATCH_FAILED",
            username="System",
            success=False,
            severity="ERROR",
            description=f"ارسال هشدار «{title}» با خطا مواجه شد: {e}",
        ))
