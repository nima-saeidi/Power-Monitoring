from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from main_api.core.database import Base

from main_api.modules.feeders.models import Feeder


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    feeder_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("feeders.id"))

    key: Mapped[str] = mapped_column(String, index=True)

    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

