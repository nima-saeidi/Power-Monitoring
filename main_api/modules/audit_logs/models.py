
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from main_api.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=True)
    user_role = Column(String(20), nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    action = Column(String(100), index=True, nullable=False)
    resource_type = Column(String(50), index=True, nullable=True)
    resource_id = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)

    changes = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)

    success = Column(Boolean, default=True)
    error_message = Column(String(500), nullable=True)
    severity = Column(String(20), default="INFO")


class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)

    command_type = Column(String(50), index=True, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="SET NULL"), nullable=True)
    target = Column(String(100), nullable=True)

    parameters = Column(JSON, nullable=True)
    modbus_function = Column(Integer, nullable=True)
    register_address = Column(Integer, nullable=True)

    success = Column(Boolean, default=True, index=True)
    response = Column(JSON, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)


class DeviceTestLog(Base):
    __tablename__ = "device_test_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    tested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), nullable=True)

    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)

    test_type = Column(String(50), index=True, nullable=False)

    success = Column(Boolean, default=True)
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(String(500), nullable=True)
