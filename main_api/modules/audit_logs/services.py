import json
import logging
import aio_pika
from typing import Optional, Dict, Any
from datetime import datetime
from math import ceil
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from main_api.modules.audit_logs.repository import (
    AuditLogRepository,
    CommandLogRepository,
    DeviceTestLogRepository
)
from main_api.modules.audit_logs.schemas import (
    AuditLogResponse,
    AuditLogListResponse,
    CommandLogResponse,
    CommandLogListResponse,
    UserActivityResponse,
    DeviceTestLogListResponse,
    DeviceTestLogResponse
)
# اگر UserRepository در جای دیگری است آن را ایمپورت کنید
from main_api.modules.users.repository import UserRepository

# TODO: این ایمپورت را بر اساس ساختار پروژه خود تنظیم کنید
# from main_api.core.settings import settings

logger = logging.getLogger(__name__)

# ============================================================================
#                            RABBITMQ PRODUCERS
# ============================================================================

# بهتر است آدرس از فایل تنظیمات خوانده شود: settings.RABBITMQ_URL
RABBITMQ_URL = "amqp://GAPGPTMASKTOKEN27xx0c09w7mX0X:GAPGPTMASKTOKEN27xx0c09w7mX1X@localhost:5672/"
LOGS_QUEUE_NAME = "logs_queue"


async def publish_log_to_rabbitmq(log_type: str, payload: Dict[str, Any]):
    """تابع پایه برای ارسال لاگ به RabbitMQ"""
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # اطمینان از وجود صف (Durable برای از دست نرفتن لاگ‌ها هنگام ریستارت شدن RabbitMQ)
            queue = await channel.declare_queue(LOGS_QUEUE_NAME, durable=True)

            message_body = {
                "service_name": "main_api",
                "log_type": log_type,
                "data": payload
            }

            message = aio_pika.Message(
                body=json.dumps(message_body, default=str).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await channel.default_exchange.publish(
                message,
                routing_key=LOGS_QUEUE_NAME
            )
    except Exception as e:
        logger.error(f"Failed to send {log_type} log to RabbitMQ: {e}")


async def send_audit_log(
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        severity: str = "INFO",
        **kwargs
):
    """ارسال لاگ‌های عمومی و امنیتی (ورود، تغییرات سیستم، خطاها)"""
    payload = {
        "action": action,
        "user_id": user_id,
        "username": username,
        "user_role": user_role,
        "ip_address": ip_address,
        "success": success,
        "severity": severity,
        **kwargs  # فیلدهایی مثل description, resource_type, old_value, new_value
    }
    await publish_log_to_rabbitmq("audit", payload)


async def send_command_log(
        command_type: str,
        user_id: Optional[int] = None,
        success: bool = True,
        **kwargs
):
    """ارسال لاگ‌های مربوط به دستورات مدباس"""
    payload = {
        "command_type": command_type,
        "user_id": user_id,
        "success": success,
        **kwargs  # فیلدهایی مثل post_id, feeder_id, command_data, error_message
    }
    await publish_log_to_rabbitmq("command", payload)


async def send_device_test_log(
        test_type: str,
        success: bool = True,
        **kwargs
):
    """ارسال لاگ‌های تست دستگاه‌ها"""
    payload = {
        "test_type": test_type,
        "success": success,
        **kwargs  # فیلدهایی مثل device_id, test_result, latency, error_message
    }
    await publish_log_to_rabbitmq("device_test", payload)


# ============================================================================
#                               SERVICES
# ============================================================================

class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_logs(
            self, user_id: Optional[int], action: Optional[str],
            resource_type: Optional[str], severity: Optional[str],
            success: Optional[bool], start_date: Optional[datetime],
            end_date: Optional[datetime], page: int, page_size: int
    ) -> AuditLogListResponse:

        skip = (page - 1) * page_size
        severity_upper = severity.upper() if severity else None

        logs, total = await AuditLogRepository.get_logs(
            db=self.db, user_id=user_id, action=action, resource_type=resource_type,
            severity=severity_upper, success=success, start_date=start_date,
            end_date=end_date, skip=skip, limit=page_size
        )
        pages = ceil(total / page_size) if total > 0 else 0

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total, page=page, page_size=page_size, pages=pages
        )

    async def search_logs(self, q: str, page: int, page_size: int) -> AuditLogListResponse:
        skip = (page - 1) * page_size
        logs, total = await AuditLogRepository.search_logs(
            db=self.db, search_term=q, skip=skip, limit=page_size
        )
        pages = ceil(total / page_size) if total > 0 else 0

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total, page=page, page_size=page_size, pages=pages
        )

    async def get_log_by_id(self, log_id: int) -> AuditLogResponse:
        log = await AuditLogRepository.get_by_id(self.db, log_id)
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
        return AuditLogResponse.model_validate(log)

    async def get_user_activity(self, user_id: int, days: int) -> UserActivityResponse:
        target_user = await UserRepository.get_by_id(self.db, user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        logs = await AuditLogRepository.get_user_activity(self.db, user_id, days)
        total_actions = len(logs)
        successful_actions = sum(1 for log in logs if log.success)

        return UserActivityResponse(
            user_id=user_id,
            username=target_user.username,
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=total_actions - successful_actions,
            recent_logs=[AuditLogResponse.model_validate(log) for log in logs[:50]],
            period_days=days
        )

    async def purge_old_logs(self, days: int, current_user) -> dict:
        deleted_count = await AuditLogRepository.delete_old_logs(self.db, days)

        # تغییر مهم: ارسال لاگ به RabbitMQ به جای ذخیره مستقیم در دیتابیس
        await send_audit_log(
            action="PURGE_AUDIT_LOGS",
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role,
            resource_type="system",
            description=f"Purged {deleted_count} logs older than {days} days.",
            severity="WARNING"
        )

        return {"success": True, "message": f"Successfully deleted {deleted_count} logs.",
                "deleted_count": deleted_count}


class CommandLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_command_logs(
            self, post_id: Optional[int], feeder_id: Optional[int],
            user_id: Optional[int], start_date: Optional[datetime],
            end_date: Optional[datetime], page: int, page_size: int
    ) -> CommandLogListResponse:
        skip = (page - 1) * page_size
        logs, total = await CommandLogRepository.get_command_history(
            db=self.db, post_id=post_id, feeder_id=feeder_id, user_id=user_id,
            start_date=start_date, end_date=end_date, skip=skip, limit=page_size
        )
        pages = ceil(total / page_size) if total > 0 else 0

        return CommandLogListResponse(
            items=[CommandLogResponse.model_validate(log) for log in logs],
            total=total, page=page, page_size=page_size, pages=pages
        )

    async def get_failed_commands(self, hours: int) -> CommandLogListResponse:
        logs = await CommandLogRepository.get_failed_commands(self.db, hours)
        return CommandLogListResponse(
            items=[CommandLogResponse.model_validate(log) for log in logs],
            total=len(logs), page=1, page_size=len(logs), pages=1
        )


class DeviceTestLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recent_tests(self, limit: int) -> DeviceTestLogListResponse:
        logs = await DeviceTestLogRepository.get_recent_tests(self.db, limit)
        return DeviceTestLogListResponse(
            items=[DeviceTestLogResponse.model_validate(log) for log in logs],
            total=len(logs), page=1, page_size=len(logs), pages=1
        )
