import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base  # مسیر Base خود را در صورت نیاز اصلاح کنید


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    # شناسه خود رکورد همچنان می‌تواند UUID بماند
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # ❌ (حذف شد) تعریف اشتباه به عنوان UUID: 
    # post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), index=True)

    # ✅ تعریف صحیح کلید خارجی به عنوان Integer (هماهنگ با جدول posts)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    feeder_id:Mapped[int] = mapped_column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    key: Mapped[str] = mapped_column(String, index=True)

    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ✅ تعریف relationship برای رفع خطای Mapper
    # دقت کنید در مدل Post هم باید timeseries_data = relationship("TimeseriesData", back_populates="post") داشته باشید
    post = relationship("Post", back_populates="timeseries_data")
    feeder = relationship("Feeder", back_populates="timeseries_data")
