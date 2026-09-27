import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from math import ceil
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, BackgroundTasks

from main_api.core.config import settings
from main_api.core.broker import message_broker
from main_api.core.errors import api_error
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


LOGS_QUEUE_NAME = "logs_queue"


async def publish_log_to_rabbitmq(
        service_name: str,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
):
    message_body = {
        "service_name": service_name,
        "action": action,
        "user_id": user_id,
        "details": details,
    }

    success = await message_broker.publish_to_queue(LOGS_QUEUE_NAME, message_body)
    if not success:
        logger.error(f"Failed to send '{action}' log to RabbitMQ.")


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
    details = {
        "username": username,
        "user_role": user_role,
        "ip_address": ip_address,
        "success": success,
        "severity": severity.upper(),
        **kwargs,
    }
    await publish_log_to_rabbitmq(service_name=service_name, action=action, details=details, user_id=user_id)


def schedule_audit_log(background_tasks: Optional[BackgroundTasks], **kwargs):
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
    details = {
        "success": success,
        **kwargs,
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
    details = {
        "success": success,
        **kwargs,
    }
    await publish_log_to_rabbitmq(
        service_name=service_name, action=f"DEVICE_TEST_{test_type.upper()}", details=details
    )



class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_url = settings.LOGGING_SERVICE_URL.rstrip("/")

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            logger.error(f"Cannot reach logging_service at {url}: {exc}")
            raise api_error(
                status.HTTP_503_SERVICE_UNAVAILABLE, "LOGGING_SERVICE_UNAVAILABLE",
                f"سرویس لاگ در دسترس نیست: {exc}"
            )
        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = None
            detail = body.get("detail") if isinstance(body, dict) else None
            if isinstance(detail, dict) and "message" in detail:
                raise HTTPException(status_code=response.status_code, detail=detail)
            message = detail if isinstance(detail, str) else response.text
            raise api_error(
                response.status_code, "LOGGING_SERVICE_ERROR",
                message or "خطای نامشخص از سرویس لاگ"
            )
        return response.json()

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
