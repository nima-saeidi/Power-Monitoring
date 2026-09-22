import json
import logging
import asyncio
import aio_pika
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from math import ceil
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, BackgroundTasks

from main_api.core.config import settings
from main_api.modules.audit_logs.repository import (
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

logger = logging.getLogger(__name__)

# ============================================================================
#                            RABBITMQ PRODUCERS
# ============================================================================
# این تابع مسیر واحد و کانونیِ ارسال هر رویدادی است که باید در سیستم ثبت شود
# (لاگین/خروج، خطاها، ارسال نوتیفیکیشن، درخواست‌های ناموفق و ...). پیام دقیقاً
# با ساختار LogCreate سرویس لاگ (logging_service) منتشر می‌شود تا کانسومر آن
# بتواند بدون خطای اعتبارسنجی، آن را در PostgreSQL ذخیره و به Graylog بفرستد.

LOGS_QUEUE_NAME = "logs_queue"


async def publish_log_to_rabbitmq(
        service_name: str,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
):
    """انتشار مستقیم یک پیام لاگ (با ساختار منطبق بر LogCreate) به صف logs_queue"""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # اطمینان از وجود صف (Durable برای از دست نرفتن لاگ‌ها هنگام ریستارت شدن RabbitMQ)
            await channel.declare_queue(LOGS_QUEUE_NAME, durable=True)

            message_body = {
                "service_name": service_name,
                "action": action,
                "user_id": user_id,
                "details": details,
            }

            message = aio_pika.Message(
                body=json.dumps(message_body, default=str).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )

            # صف مقصد با نام دقیق صف، روی Default Exchange مسیریابی مستقیم می‌شود
            await channel.default_exchange.publish(message, routing_key=LOGS_QUEUE_NAME)
    except Exception as e:
        logger.error(f"Failed to send '{action}' log to RabbitMQ: {e}")


async def send_audit_log(
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        severity: str = "INFO",
        service_name: str = "main_api",
        **kwargs
):
    """ارسال لاگ‌های عمومی و امنیتی (ورود، تغییرات سیستم، خطاها، نوتیفیکیشن‌ها و ...)"""
    details = {
        "username": username,
        "user_role": user_role,
        "ip_address": ip_address,
        "success": success,
        "severity": severity.upper(),
        **kwargs,  # فیلدهایی مثل description, resource_type, old_value, new_value
    }
    await publish_log_to_rabbitmq(service_name=service_name, action=action, details=details, user_id=user_id)


def schedule_audit_log(background_tasks: Optional[BackgroundTasks], **kwargs):
    """
    ثبت audit log بدون بلاک کردن پاسخ درخواست.
    اگر BackgroundTasks در دسترس باشد (درخواست موفق و پاسخ در حال آماده شدن است)
    از آن استفاده می‌شود، در غیر این صورت (مثلاً درست قبل از raise کردن یک خطا)
    به‌صورت fire-and-forget با asyncio.create_task ارسال می‌شود.
    """
    if background_tasks is not None:
        background_tasks.add_task(send_audit_log, **kwargs)
    else:
        asyncio.create_task(send_audit_log(**kwargs))


async def send_command_log(
        command_type: str,
        user_id: Optional[int] = None,
        success: bool = True,
        service_name: str = "main_api",
        **kwargs
):
    """ارسال لاگ‌های مربوط به دستورات مدباس"""
    details = {
        "success": success,
        **kwargs,  # فیلدهایی مثل post_id, feeder_id, command_data, error_message
    }
    await publish_log_to_rabbitmq(
        service_name=service_name, action=f"COMMAND_{command_type.upper()}", details=details, user_id=user_id
    )


async def send_device_test_log(
        test_type: str,
        success: bool = True,
        service_name: str = "main_api",
        **kwargs
):
    """ارسال لاگ‌های تست دستگاه‌ها"""
    details = {
        "success": success,
        **kwargs,  # فیلدهایی مثل device_id, test_result, latency, error_message
    }
    await publish_log_to_rabbitmq(
        service_name=service_name, action=f"DEVICE_TEST_{test_type.upper()}", details=details
    )


# ============================================================================
#                               SERVICES (Read Side)
# ============================================================================
# نکته‌ی معماری مهم: خواندن لاگ‌ها دیگر از یک جدول محلی در main_api انجام
# نمی‌شود (آن جدول هیچ‌وقت پر نمی‌شد چون نوشتن همیشه از طریق RabbitMQ به
# logging_service انجام می‌گیرد). به‌جای آن AuditLogService به‌عنوان یک پروکسی
# نازک روی API واقعی logging_service عمل می‌کند تا پنل ادمین همیشه داده‌ی واقعی
# و به‌روز ببیند.

class AuditLogService:
    def __init__(self, db: AsyncSession):
        # db برای این سرویس دیگر لازم نیست (منبع داده logging_service است) اما
        # برای سازگاری با امضای قبلی dependency نگه داشته شده.
        self.db = db
        self.base_url = settings.LOGGING_SERVICE_URL.rstrip("/")

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            logger.error(f"Cannot reach logging_service at {url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"سرویس لاگ در دسترس نیست: {exc}"
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

    @staticmethod
    def _paginate(total: int, page: int, page_size: int) -> Dict[str, int]:
        pages = ceil(total / page_size) if total > 0 else 0
        return {"total": total, "page": page, "page_size": page_size, "pages": pages}

    async def get_logs(
            self, user_id: Optional[int], action: Optional[str],
            service_name: Optional[str], severity: Optional[str],
            success: Optional[bool], start_date: Optional[datetime],
            end_date: Optional[datetime], page: int, page_size: int
    ) -> AuditLogListResponse:
        offset = (page - 1) * page_size
        data = await self._get("/logs", {
            "user_id": user_id, "action": action, "service_name": service_name,
            "severity": severity, "success": success,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": page_size, "offset": offset,
        })
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(item) for item in data.get("items", [])],
            **self._paginate(data.get("total", 0), page, page_size)
        )

    async def search_logs(self, q: str, page: int, page_size: int) -> AuditLogListResponse:
        offset = (page - 1) * page_size
        data = await self._get("/logs", {"search": q, "limit": page_size, "offset": offset})
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(item) for item in data.get("items", [])],
            **self._paginate(data.get("total", 0), page, page_size)
        )

    async def get_log_by_id(self, log_id: int) -> AuditLogResponse:
        data = await self._get(f"/logs/{log_id}", {})
        return AuditLogResponse.model_validate(data)

    async def get_filter_options(self) -> Dict[str, Any]:
        return await self._get("/logs/meta/filters", {})

    async def get_user_activity(self, user_id: int, days: int) -> UserActivityResponse:
        start_date = datetime.utcnow() - timedelta(days=days)
        data = await self._get("/logs", {"user_id": user_id, "start_date": start_date.isoformat(), "limit": 1000})
        items = [AuditLogResponse.model_validate(item) for item in data.get("items", [])]
        total_actions = len(items)
        successful_actions = sum(1 for log in items if (log.details or {}).get("success", True))

        return UserActivityResponse(
            user_id=user_id,
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=total_actions - successful_actions,
            recent_logs=items[:50],
            period_days=days
        )

    async def purge_old_logs(self, days: int, current_user) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.delete(f"{self.base_url}/logs", params={"older_than_days": days})
            response.raise_for_status()
            deleted_count = response.json().get("deleted_count", 0)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"سرویس لاگ در دسترس نیست: {exc}")

        await send_audit_log(
            action="PURGE_AUDIT_LOGS",
            user_id=current_user.id,
            username=current_user.email,
            user_role=current_user.role,
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
