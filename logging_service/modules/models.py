from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from core.database import Base

class AuditLog(Base):
    __tablename__ = "service_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_name = Column(String(50), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
