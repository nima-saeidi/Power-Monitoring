# main_api/modules/users/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from main_api.core.database import Base
from sqlalchemy.orm import relationship
import enum


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    TECHNICAL_OPERATOR = "technical_operator"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone_number = Column(String(15), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.USER, nullable=False)
    is_active = Column(Boolean, default=True)

    # فیلد جدید برای فعال/غیرفعال بودن نوتیفیکیشن پیامکی
    sms_notification_enabled = Column(Boolean, default=False)

    # وضعیت قفل حساب بر اساس تنظیمات max_login_attempts / lockout_duration_minutes
    # (تنظیمات سیستم -> main_api/modules/settings)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False,
                                            cascade="all, delete-orphan")
