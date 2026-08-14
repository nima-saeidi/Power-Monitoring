from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from main_api.core.database import Base


class NotificationType(str, enum.Enum):
    """انواع نوتیفیکیشن"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ALERT = "alert"


class NotificationPriority(str, enum.Enum):
    """اولویت نوتیفیکیشن"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Notification(Base):
    """مدل نوتیفیکیشن"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(SQLEnum(NotificationType), nullable=False, default=NotificationType.INFO)
    priority = Column(SQLEnum(NotificationPriority), nullable=False, default=NotificationPriority.MEDIUM)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # منبع نوتیفیکیشن (مثلاً post_id، feeder_id)
    source_type = Column(String(50), nullable=True, index=True)
    source_id = Column(Integer, nullable=True)

    # اطلاعات اضافی (تغییر نام از metadata به meta_data به دلیل رزرو بودن کلمه در SQLAlchemy)
    meta_data = Column(JSONB, nullable=True)

    # وضعیت‌ها
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    is_dismissed = Column(Boolean, default=False, nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Action URL (برای redirect کاربر)
    action_url = Column(String(500), nullable=True)

    # زمان‌ها
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, title='{self.title}')>"


class NotificationTemplate(Base):
    """قالب‌های از پیش تعریف شده برای نوتیفیکیشن"""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    type = Column(SQLEnum(NotificationType), nullable=False)
    priority = Column(SQLEnum(NotificationPriority), nullable=False)

    title_template = Column(String(255), nullable=False)
    message_template = Column(Text, nullable=False)

    # متغیرهای قابل استفاده در template (JSON)
    variables = Column(JSONB, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, name='{self.name}')>"


class NotificationPreference(Base):
    """تنظیمات نوتیفیکیشن کاربر"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # فعال/غیرفعال کردن انواع نوتیفیکیشن
    enable_info = Column(Boolean, default=True, nullable=False)
    enable_warning = Column(Boolean, default=True, nullable=False)
    enable_error = Column(Boolean, default=True, nullable=False)
    enable_success = Column(Boolean, default=True, nullable=False)
    enable_alert = Column(Boolean, default=True, nullable=False)

    # فیلتر بر اساس اولویت
    min_priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.LOW, nullable=False)

    # تنظیمات نمایش
    auto_dismiss_after_read = Column(Boolean, default=False, nullable=False)
    auto_dismiss_delay_minutes = Column(Integer, default=5, nullable=True)

    # حداکثر نوتیفیکیشن‌های نمایشی
    max_display_count = Column(Integer, default=50, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreference(user_id={self.user_id})>"
