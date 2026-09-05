from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

# ⚠️ بسیار مهم: Base را باید از فایل database.py همین سرویس (postgres_storage_service) ایمپورت کنید
# به هیچ وجه نباید از main_api چیزی ایمپورت شود.
from .database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    location_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    address = Column(String(255), nullable=True)

    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    children = relationship("Location", back_populates="parent", lazy="selectin", cascade="all, delete-orphan")
    parent = relationship("Location", back_populates="children", remote_side="[Location.id]", lazy="selectin")
    posts = relationship("Post", back_populates="location")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)

    supply_source = Column(String(150), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    transformer_specs = Column(String(200), nullable=True)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, default=502)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    metadata_info = Column("metadata", JSONB, nullable=True)

    # فیلدهایی که این سرویس (کانسومر) معمولاً آپدیت می‌کند:
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    location = relationship("Location", back_populates="posts")
    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")
    outgoing_links = relationship("Link", foreign_keys="[Link.from_post_id]", back_populates="from_post")
    incoming_links = relationship("Link", foreign_keys="[Link.to_post_id]", back_populates="to_post")


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

    metadata_info = Column("metadata", JSONB, nullable=True)

    # فیلدهایی که این سرویس (کانسومر) معمولاً آپدیت می‌کند:
    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="feeders")

    __table_args__ = (
        Index('idx_feeder_post', 'post_id'),
    )


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=True)

    from_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    to_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    cable_type = Column(String(50), nullable=True)
    cross_section = Column(Float, nullable=True)
    allowed_current = Column(Float, nullable=True)
    length = Column(Float, nullable=True)

    metadata_info = Column("metadata", JSONB, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    from_post = relationship("Post", foreign_keys=[from_post_id], back_populates="outgoing_links")
    to_post = relationship("Post", foreign_keys=[to_post_id], back_populates="incoming_links")
