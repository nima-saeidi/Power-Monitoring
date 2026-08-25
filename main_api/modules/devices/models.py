from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.modules.audit_logs.models import CommandLog
from main_api.core.database import Base
from sqlalchemy.sql import func


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feeder_id = Column(Integer, index=True, nullable=False)
    key = Column(String, index=True, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True, nullable=False)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    location_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    address = Column(String(255), nullable=True, doc="آدرس متنی موقعیت")

    parent_id = Column(
        Integer,
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ========================================================
    # SELF RELATIONSHIP
    # ========================================================
    children = relationship(
        "Location",
        back_populates="parent",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    parent = relationship(
        "Location",
        back_populates="children",
        remote_side="[Location.id]",
        lazy="selectin"
    )

    # ========================================================
    # POSTS
    # ========================================================
    # روابط قبلی (campus_posts و unit_posts) که ارجاع به ستون‌های حذف شده داشتند پاک شدند
    posts = relationship(
        "Post",
        back_populates="location"
    )


# =========================================
# مدل پست
# =========================================
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)

    # --- اطلاعات پایه ---
    supply_source = Column(String(150), nullable=True)  # محل تغذیه

    # موقعیت کلی (فقط location_id باقی مانده است)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    transformer_specs = Column(String(200), nullable=True)  # مشخصات ترانس
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, default=502)

    # --- موقعیت مکانی ---
    latitude = Column(Float, nullable=True)  # عرض جغرافیایی
    longitude = Column(Float, nullable=True)  # طول جغرافیایی

    metadata_info = Column("metadata", JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    consecutive_failures = Column(Integer, default=0)

    # روابط
    location = relationship("Location", back_populates="posts")
    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")

    outgoing_links = relationship("Link", foreign_keys="[Link.from_post_id]", back_populates="from_post")
    incoming_links = relationship("Link", foreign_keys="[Link.to_post_id]", back_populates="to_post")


# =========================================
# مدل فیدر
# =========================================
class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    # --- اطلاعات پایه فیدر ---
    feeder_type = Column(String(50), nullable=True)  # نوع فیدر: تولید کننده / مصرف کننده
    max_current = Column(Float, nullable=True)  # حداکثر جریان (A)

    # --- تنظیمات ارتباطی شبکه و مدباس ---
    ip_address = Column(String(50), nullable=True)  # آدرس IP فیدر
    port = Column(Integer, nullable=True)  # پورت ارتباطی
    modbus_address = Column(Integer, nullable=True)  # آدرس مدباس (Slave ID / Unit ID)

    # --- رجیسترهای پارامترهای اصلی مدباس ---
    active_power_register = Column(Integer, nullable=True)
    reactive_power_register = Column(Integer, nullable=True)
    voltage_register = Column(Integer, nullable=True)
    current_register = Column(Integer, nullable=True)
    power_factor_register = Column(Integer, nullable=True)

    metadata_info = Column("metadata", JSONB, nullable=True)

    # --- وضعیت و مانیتورینگ ---
    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- روابط ---
    post = relationship("Post", back_populates="feeders")

    __table_args__ = (
        Index('idx_feeder_post', 'post_id'),
    )


# =========================================
# مدل لینک ارتباطی
# =========================================
class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=True)

    from_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    to_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    cable_type = Column(String(50), nullable=True)  # نوع سیم
    cross_section = Column(Float, nullable=True)  # سطح مقطع
    allowed_current = Column(Float, nullable=True)  # جریان مجاز (A)
    length = Column(Float, nullable=True)  # طول لینک

    metadata_info = Column("metadata", JSONB, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    from_post = relationship("Post", foreign_keys=[from_post_id], back_populates="outgoing_links")
    to_post = relationship("Post", foreign_keys=[to_post_id], back_populates="incoming_links")
