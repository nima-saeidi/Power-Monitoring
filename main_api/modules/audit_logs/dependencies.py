from fastapi import Depends
from sqlalchemy.orm import Session

# ۱. تابع گرفتن سشن دیتابیس را ایمپورت کنید
from main_api.core.database import get_db


# ۲. ریپازیتوری‌های لاگ را ایمپورت کنید
from .modules.logs.repositories.audit_log_repository import AuditLogRepository
from .modules.logs.repositories.command_log_repository import CommandLogRepository
from .modules.logs.repositories.device_test_log_repository import DeviceTestLogRepository


# ۳. برای هر ریپازیتوری یک تابع فراهم‌کننده (provider) بسازید

def get_audit_log_repo(db: Session = Depends(get_db)) -> AuditLogRepository:
    """
    Dependency provider for AuditLogRepository.
    """
    return AuditLogRepository(db)

def get_command_log_repo(db: Session = Depends(get_db)) -> CommandLogRepository:
    """
    Dependency provider for CommandLogRepository.
    """
    return CommandLogRepository(db)

def get_device_test_log_repo(db: Session = Depends(get_db)) -> DeviceTestLogRepository:
    """
    Dependency provider for DeviceTestLogRepository.
    """
    return DeviceTestLogRepository(db)
