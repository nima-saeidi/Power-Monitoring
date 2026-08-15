from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class AuditLog(Base):
    """لاگ‌های ممیزی سیستم - تمام عملیات‌ها"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # کاربر
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    user_role = Column(String(20), nullable=True)
    
    # منبع درخواست
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # عملیات
    action = Column(String(100), nullable=False, index=True)  # 'login', 'logout', 'create_post', 'update_feeder', etc.
    resource_type = Column(String(50), nullable=True)  # 'post', 'feeder', 'user', 'settings'
    resource_id = Column(Integer, nullable=True)
    
    # جزئیات
    description = Column(Text, nullable=True)
    changes = Column(JSONB, nullable=True)  # تغییرات قبل/بعد
    meta_data = Column(JSONB, nullable=True)  # تغییر نام از metadata به meta_data
    
    # نتیجه
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    
    # Severity level
    severity = Column(String(20), default='info')  # 'debug', 'info', 'warning', 'error', 'critical'

    # روابط
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_user', 'user_id', 'timestamp'),
        Index('idx_audit_action', 'action', 'timestamp'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


class CommandLog(Base):
    """لاگ دستورات Modbus و کنترلی"""
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # کاربر و منبع
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # دستور
    command_type = Column(String(50), nullable=False)  # 'read', 'write', 'control', 'config'
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="SET NULL"), nullable=True)
    target = Column(String(200), nullable=True)  # آدرس یا نام دستگاه
    
    # پارامترها
    parameters = Column(JSONB, nullable=True)  # پارامترهای ورودی
    modbus_function = Column(Integer, nullable=True)  # کد تابع Modbus
    register_address = Column(Integer, nullable=True)
    
    # نتیجه
    success = Column(Boolean, nullable=False)
    response = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)  # زمان پاسخ به میلی‌ثانیه
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # روابط (نکته: در کلاس‌های User, Post و Feeder نیز باید command_logs تعریف شده باشد)
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
    """لاگ تست‌های ارتباطی دستگاه‌ها"""
    __tablename__ = "device_test_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # دستگاه
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), nullable=True)
    device_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    
    # کاربر تست‌کننده
    tested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # نوع تست
    test_type = Column(String(50), nullable=False)  # 'ping', 'modbus', 'connection'
    
    # نتیجه تست
    success = Column(Boolean, nullable=False, default=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # روابط
    tested_by_user = relationship("User", foreign_keys=[tested_by_user_id])
    post = relationship("Post", foreign_keys=[post_id])
    feeder = relationship("Feeder", foreign_keys=[feeder_id])
