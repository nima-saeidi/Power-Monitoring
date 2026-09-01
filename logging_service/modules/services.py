import logging
from typing import Optional
from sqlalchemy import select, func, or_
from core.database import AsyncSessionLocal
from modules.models import AuditLog
from modules.schemas import LogFilterRequest, LogListResponse, LogItem

logger = logging.getLogger(__name__)


class LoggingService:

    @staticmethod
    async def save_log(log_data: dict) -> AuditLog:
        """ذخیره‌سازی پیام دریافتی از صف RabbitMQ در دیتابیس PostgreSQL"""
        async with AsyncSessionLocal() as session:
            try:
                # استخراج فیلدهای اصلی و تفکیک details
                service_name = log_data.get("service_name", "main_api")
                action = log_data.get("action", "UNKNOWN")
                user_id = log_data.get("user_id")
                details = log_data.get("details", log_data)

                new_log = AuditLog(
                    service_name=service_name,
                    action=action,
                    user_id=user_id,
                    details=details
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
    async def get_logs(filters: LogFilterRequest) -> LogListResponse:
        """دریافت و فیلتر لاگ‌ها از دیتابیس PostgreSQL به صورت Async"""
        async with AsyncSessionLocal() as session:
            # ساخت کوئری پایه
            query = select(AuditLog)
            count_query = select(func.count(AuditLog.id))

            # اعمال فیلترها
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

            if conditions:
                query = query.where(*conditions)
                count_query = count_query.where(*conditions)

            # دریافت تعداد کل رکوردها
            total_result = await session.execute(count_query)
            total = total_result.scalar_one_or_none() or 0

            # صفحه‌بندی و مرتب‌سازی بر اساس جدیدترین
            query = query.order_by(AuditLog.created_at.desc()).offset(filters.offset).limit(filters.limit)
            result = await session.execute(query)
            logs = result.scalars().all()

            # تبدیل به Schema خروجی
            items = [LogItem.model_validate(log) for log in logs]
            return LogListResponse(total=total, items=items)


logging_service_instance = LoggingService()
