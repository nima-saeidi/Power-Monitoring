import logging
import time
from typing import Optional
from sqlalchemy import select, func, or_
from core.database import AsyncSessionLocal
from modules.models import AuditLog
from modules.schemas import (
    LogFilterRequest,
    LogListResponse,
    LogItem,
    LogCreate,
    LogFilterOptionsResponse,
)

logger = logging.getLogger(__name__)

_FILTER_OPTIONS_CACHE_TTL_SECONDS = 300
_filter_options_cache: dict = {"data": None, "expires_at": 0.0}


class LoggingService:

    @staticmethod
    async def save_log(log_data: LogCreate) -> AuditLog:
        async with AsyncSessionLocal() as session:
            try:
                new_log = AuditLog(
                    service_name=log_data.service_name,
                    action=log_data.action,
                    user_id=log_data.user_id,
                    details=log_data.details
                )
                session.add(new_log)
                await session.commit()
                await session.refresh(new_log)
                logger.info(f"Audit log saved successfully (ID: {new_log.id})")
                return new_log
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save log to PostgreSQL: {e}")
                raise e

    @staticmethod
    def _apply_filters(query, filters: LogFilterRequest):
        conditions = []
        if filters.service_name:
            conditions.append(AuditLog.service_name == filters.service_name)
        if filters.action:
            conditions.append(AuditLog.action == filters.action)
        if filters.user_id is not None:
            conditions.append(AuditLog.user_id == filters.user_id)
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    AuditLog.action.ilike(search_term),
                    AuditLog.service_name.ilike(search_term)
                )
            )
        if filters.severity:
            conditions.append(AuditLog.details["severity"].astext == filters.severity.upper())
        if filters.success is not None:
            conditions.append(AuditLog.details["success"].astext == ("true" if filters.success else "false"))
        if filters.start_date:
            conditions.append(AuditLog.created_at >= filters.start_date)
        if filters.end_date:
            conditions.append(AuditLog.created_at <= filters.end_date)

        if conditions:
            query = query.where(*conditions)
        return query

    @staticmethod
    async def get_logs(filters: LogFilterRequest) -> LogListResponse:
        async with AsyncSessionLocal() as session:
            total_count_col = func.count().over().label("total_count")
            query = LoggingService._apply_filters(select(AuditLog, total_count_col), filters)
            query = query.order_by(AuditLog.created_at.desc()).offset(filters.offset).limit(filters.limit)

            result = await session.execute(query)
            rows = result.all()

            total = rows[0].total_count if rows else 0
            items = [LogItem.model_validate(row[0]) for row in rows]
            return LogListResponse(total=total, items=items)

    @staticmethod
    async def get_log_by_id(log_id: int) -> Optional[LogItem]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
            log = result.scalar_one_or_none()
            return LogItem.model_validate(log) if log else None

    @staticmethod
    async def get_filter_options() -> LogFilterOptionsResponse:
        now = time.monotonic()
        cached = _filter_options_cache
        if cached["data"] is not None and now < cached["expires_at"]:
            return cached["data"]

        async with AsyncSessionLocal() as session:
            services_result = await session.execute(
                select(AuditLog.service_name).where(AuditLog.service_name.is_not(None)).distinct()
            )
            actions_result = await session.execute(
                select(AuditLog.action).where(AuditLog.action.is_not(None)).distinct()
            )
            services = sorted([s for s in services_result.scalars().all() if s])
            actions = sorted([a for a in actions_result.scalars().all() if a])
            data = LogFilterOptionsResponse(services=services, actions=actions)

        cached["data"] = data
        cached["expires_at"] = now + _FILTER_OPTIONS_CACHE_TTL_SECONDS
        return data


logging_service_instance = LoggingService()
