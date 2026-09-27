from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base
from sqlalchemy.sql import func


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feeder_id = Column(Integer, index=True, nullable=False)
    key = Column(String, index=True, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True, nullable=False)


class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    feeder_type = Column(String(50), nullable=True)
    max_current = Column(Float, nullable=True)

    ip_address = Column(String(50), nullable=True)
    port = Column(Integer, nullable=True)
    modbus_address = Column(Integer, nullable=True)

    active_power_register = Column(Integer, nullable=True)
    reactive_power_register = Column(Integer, nullable=True)
    voltage_register = Column(Integer, nullable=True)
    current_register = Column(Integer, nullable=True)
    power_factor_register = Column(Integer, nullable=True)
    control_register = Column(Integer, nullable=True)
    load_status = Column(String(20), nullable=False, default="unknown", server_default="unknown")

    metadata_info = Column("metadata", JSONB, nullable=True)

    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="feeders")

    __table_args__ = (
        Index('idx_feeder_post', 'post_id'),
    )
