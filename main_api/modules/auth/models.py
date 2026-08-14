import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from main_api.core.database import Base
from sqlalchemy.orm import relationship


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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False,
                                            cascade="all, delete-orphan")
    command_logs = relationship("CommandLog", back_populates="user")
