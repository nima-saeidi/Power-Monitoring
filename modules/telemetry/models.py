import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base  # مسیر Base خود را در صورت نیاز اصلاح کنید


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"),
                                               index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    key: Mapped[str] = mapped_column(String, index=True)

    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Relationship to Post (در صورتی که در مدل Post هم relationship را تعریف کرده‌اید)
    post = relationship("Post", back_populates="timeseries_data")
