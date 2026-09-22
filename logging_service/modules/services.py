import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, or_, delete
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


class LoggingService:

    @staticmethod
    async def save_log(log_data: LogCreate) -> AuditLog:
        """ذخیره‌سازی پیام دریافتی و اعتبارسنجی شده از صف RabbitMQ در دیتابیس PostgreSQL"""
        async with AsyncSessionLocal() as session:
            try:
                # استفاده مستقیم از فیلدهای مدل Pydantic
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
        """دریافت و فیلتر لاگ‌ها از دیتابیس PostgreSQL به صورت Async"""
        async with AsyncSessionLocal() as session:
            query = LoggingService._apply_filters(select(AuditLog), filters)
            count_query = LoggingService._apply_filters(select(func.count(AuditLog.id)), filters)

            total_result = await session.execute(count_query)
            total = total_result.scalar_one_or_none() or 0

            query = query.order_by(AuditLog.created_at.desc()).offset(filters.offset).limit(filters.limit)
            result = await session.execute(query)
            logs = result.scalars().all()

            items = [LogItem.model_validate(log) for log in logs]
            return LogListResponse(total=total, items=items)

    @staticmethod
    async def get_log_by_id(log_id: int) -> Optional[LogItem]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
            log = result.scalar_one_or_none()
            return LogItem.model_validate(log) if log else None

    @staticmethod
    async def get_filter_options() -> LogFilterOptionsResponse:
        """لیست مقادیر یکتای service_name و action برای ساخت فیلترهای پنل ادمین"""
        async with AsyncSessionLocal() as session:
            services_result = await session.execute(
                select(AuditLog.service_name).where(AuditLog.service_name.is_not(None)).distinct()
            )
            actions_result = await session.execute(
                select(AuditLog.action).where(AuditLog.action.is_not(None)).distinct()
            )
            services = sorted([s for s in services_result.scalars().all() if s])
            actions = sorted([a for a in actions_result.scalars().all() if a])
            return LogFilterOptionsResponse(services=services, actions=actions)

    @staticmethod
    async def purge_old_logs(older_than_days: int) -> int:
        """حذف لاگ‌های قدیمی‌تر از تعداد روز مشخص شده"""
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            await session.commit()
            return result.rowcount or 0


logging_service_instance = LoggingService()
