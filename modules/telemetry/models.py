import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base  # مسیر Base خود را در صورت نیاز اصلاح کنید


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # ✅ اصلاح شد: هم Type Hint به int | None تغییر کرد، هم nullable=True اضافه شد
    post_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=True)
    
    # ✅ اصلاح شد: هم Type Hint به int | None تغییر کرد، هم nullable=True اضافه شد
    feeder_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), index=True, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    key: Mapped[str] = mapped_column(String, index=True)

    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    post = relationship("Post", back_populates="timeseries_data")
    feeder = relationship("Feeder", back_populates="timeseries_data")
