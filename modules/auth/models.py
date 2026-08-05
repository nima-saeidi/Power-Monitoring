from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from core.database import Base
import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from core.database import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    TECHNICAL_OPERATOR = "technical_operator"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="admin", nullable=False)  # admin, operator, viewer
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
