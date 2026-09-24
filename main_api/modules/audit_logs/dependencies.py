# main_api/modules/audit_logs/dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from main_api.core.database import get_db

from .services import AuditLogService, CommandLogService, DeviceTestLogService

def get_audit_log_service(db: AsyncSession = Depends(get_db)) -> AuditLogService:
    return AuditLogService(db)

def get_command_log_service(db: AsyncSession = Depends(get_db)) -> CommandLogService:
    return CommandLogService(db)

def get_device_test_log_service(db: AsyncSession = Depends(get_db)) -> DeviceTestLogService:
    return DeviceTestLogService(db)
