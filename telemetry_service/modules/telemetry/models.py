import uuid
from datetime import datetime
# توجه: ForeignKey حذف شد
from sqlalchemy import String, Float, Integer, Boolean, DateTime
# توجه: relationship حذف شد
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

# نکته مهم: این Base ترجیحاً باید مربوط به خود سرویس تله‌متری باشد
from core.database import Base


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # ✅ اصلاح شد: ForeignKey حذف شد. فقط عدد ID به عنوان یک فیلد معمولی (منطقی) ذخیره می‌شود
    post_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)

    # ✅ اصلاح شد: ForeignKey حذف شد.
    feeder_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    key: Mapped[str] = mapped_column(String, index=True)

    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ✅ اصلاح شد: relationship ها کاملاً حذف شدند چون کلاس‌های Post و Feeder در این پروژه وجود ندارند
    # post = relationship("Post", back_populates="timeseries_data")
    # feeder = relationship("Feeder", back_populates="timeseries_data")
