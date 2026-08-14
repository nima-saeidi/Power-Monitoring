from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from main_api.modules.audit_logs.models import AuditLog, CommandLog
from main_api.core.logging import audit_logger


class AuditLogRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: Optional[int],
        username: Optional[str],
        user_role: Optional[str],
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        description: Optional[str] = None,
        changes: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        severity: str = 'info'
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            changes=changes,
            metadata=metadata,
            success=success,
            error_message=error_message,
            severity=severity
        )
        
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        
        audit_logger.info(
            f"AUDIT: user={username} action={action} resource={resource_type}:{resource_id} "
            f"success={success} ip={ip_address}"
        )
        
        return audit_log
    
    @staticmethod
    async def get_by_id(db: AsyncSession, log_id: int) -> Optional[AuditLog]:
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_logs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[AuditLog], int]:

        conditions = []
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if severity:
            conditions.append(AuditLog.severity == severity)
        if success is not None:
            conditions.append(AuditLog.success == success)
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)
        
        count_query = select(func.count(AuditLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total = await db.scalar(count_query)
        
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return list(logs), total or 0
    
    @staticmethod
    async def search_logs(
        db: AsyncSession,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[AuditLog], int]:

        conditions = or_(
            AuditLog.username.ilike(f"%{search_term}%"),
            AuditLog.action.ilike(f"%{search_term}%"),
            AuditLog.description.ilike(f"%{search_term}%"),
            AuditLog.ip_address.ilike(f"%{search_term}%")
        )
        
        count_query = select(func.count(AuditLog.id)).where(conditions)
        total = await db.scalar(count_query)
        
        query = (
            select(AuditLog)
            .where(conditions)
            .order_by(desc(AuditLog.timestamp))
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return list(logs), total or 0
    
    @staticmethod
    async def get_user_activity(
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> List[AuditLog]:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp >= start_date
                )
            )
            .order_by(desc(AuditLog.timestamp))
            .limit(100)
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_failed_operations(
        db: AsyncSession,
        hours: int = 24
    ) -> List[AuditLog]:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.success == False,
                    AuditLog.timestamp >= start_time
                )
            )
            .order_by(desc(AuditLog.timestamp))
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def delete_old_logs(
        db: AsyncSession,
        days: int = 90
    ) -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(AuditLog).where(AuditLog.timestamp < cutoff_date)
        )
        logs_to_delete = result.scalars().all()
        
        for log in logs_to_delete:
            await db.delete(log)
        
        await db.commit()
        return len(logs_to_delete)


class CommandLogRepository:

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: Optional[int],
        username: Optional[str],
        ip_address: Optional[str],
        command_type: str,
        post_id: Optional[int] = None,
        feeder_id: Optional[int] = None,
        target: Optional[str] = None,
        parameters: Optional[Dict] = None,
        modbus_function: Optional[int] = None,
        register_address: Optional[int] = None,
        success: bool = False,
        response: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> CommandLog:
        command_log = CommandLog(
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            command_type=command_type,
            post_id=post_id,
            feeder_id=feeder_id,
            target=target,
            parameters=parameters,
            modbus_function=modbus_function,
            register_address=register_address,
            success=success,
            response=response,
            response_time_ms=response_time_ms,
            error_message=error_message,
            error_code=error_code
        )
        
        db.add(command_log)
        await db.commit()
        await db.refresh(command_log)
        
        return command_log
    
    @staticmethod
    async def get_command_history(
        db: AsyncSession,
        post_id: Optional[int] = None,
        feeder_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[CommandLog], int]:

        conditions = []
        
        if post_id:
            conditions.append(CommandLog.post_id == post_id)
        if feeder_id:
            conditions.append(CommandLog.feeder_id == feeder_id)
        if user_id:
            conditions.append(CommandLog.user_id == user_id)
        if start_date:
            conditions.append(CommandLog.timestamp >= start_date)
        if end_date:
            conditions.append(CommandLog.timestamp <= end_date)
        
        count_query = select(func.count(CommandLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total = await db.scalar(count_query)
        
        query = select(CommandLog).order_by(desc(CommandLog.timestamp))
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        logs = list(result.scalars().all())
        
        return logs, total or 0
    
    @staticmethod
    async def get_failed_commands(
        db: AsyncSession,
        hours: int = 24
    ) -> List[CommandLog]:
        start_time = datetime.utcn