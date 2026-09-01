# logging_service/modules/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_name = Column(String(50), nullable=True, index=True)      # مثلا main_api
    action = Column(String(100), nullable=False, index=True)         # نوع عملیات
    user_id = Column(Integer, nullable=True, index=True)             # آیدی کاربری که درخواست زده
    details = Column(JSONB, nullable=True)                           # کل اطلاعات متغیر لاگ (Body، پاسخ و...)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
