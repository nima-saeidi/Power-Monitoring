from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    user_role = Column(String(20), nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    
    description = Column(Text, nullable=True)
    changes = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    
    severity = Column(String(20), default='info')  # 'debug', 'info', 'warning', 'error', 'critical'

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user_id', 'timestamp'),
        Index('idx_audit_action', 'action', 'timestamp'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    command_type = Column(String(50), nullable=False)  # 'read', 'write', 'control', 'config'
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="SET NULL"), nullable=True)
    target = Column(String(200), nullable=True)
    
    parameters = Column(JSONB, nullable=True)
    modbus_function = Column(Integer, nullable=True)
    register_address = Column(Integer, nullable=True)
    
    success = Column(Boolean, nullable=False)
    response = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    user = relationship("User", back_populates="command_logs")
    post = relationship("Post", back_populates="command_logs")
    feeder = relationship("Feeder", back_populates="command_logs")

    __table_args__ = (
        Index('idx_command_timestamp', 'timestamp'),
        Index('idx_command_user', 'user_id', 'timestamp'),
        Index('idx_command_post', 'post_id', 'timestamp'),
        Index('idx_command_success', 'success', 'timestamp'),
    )


class DeviceTestLog(Base):
    __tablename__ = "device_test_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), nullable=True)
    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    
    tested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    test_type = Column(String(50), nullable=False)  # 'ping', 'modbus', 'connection'
    
    success = Column(Boolean, nullable=False, default=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    tested_by_user = relationship("User", foreign_keys=[tested_by_user_id])
    post = relationship("Post", foreign_keys=[post_id])
    feeder = relationship("Feeder", foreign_keys=[feeder_id])
