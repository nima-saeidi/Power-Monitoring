from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from modules.audit_logs.models import CommandLog
# فرض بر این است که Base در مسیر زیر تعریف شده است
from core.database import Base


# =========================================
# مدل مکان برای ساختار درختی
# =========================================

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    location_type = Column(String(50), nullable=True)  # 'University', 'Campus', 'Building', 'Zone'
    description = Column(Text, nullable=True)

    # ساختار درختی
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط (استفاده از back_populates به جای backref برای استانداردهای جدید SQLAlchemy)
    parent = relationship("Location", remote_side=[id], back_populates="children")
    children = relationship("Location", back_populates="parent")
    
    posts = relationship("Post", back_populates="location")


# =========================================
# مدل پست
# =========================================

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)

    # ارتباط با مکان
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    # مشخصات فنی
    transformer_specs = Column(String(200), nullable=True)
    ip_address = Column(String(45), nullable=True, unique=True)
    port = Column(Integer, default=502)  # Modbus TCP default port

    # داده‌های اضافی به صورت JSONB
    metadata_info = Column("metadata", JSONB, nullable=True) 

    # وضعیت
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)  # آخرین ارتباط موفق

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    location = relationship("Location", back_populates="posts")
    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")

    # روابط با سایر ماژول‌ها (باید در main.py ایمپورت شوند تا شناخته شوند)
    timeseries_data = relationship("TimeseriesData", back_populates="post", cascade="all, delete-orphan")
    command_logs = relationship("CommandLog", back_populates="post")
    device_tests = relationship("DeviceTestLog", back_populates="post")

    # لینک‌ها
    outgoing_links = relationship("Link", foreign_keys="Link.from_post_id", back_populates="from_post")
    incoming_links = relationship("Link", foreign_keys="Link.to_post_id", back_populates="to_post")


# =========================================
# مدل فیدر
# =========================================

class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    # مشخصات فنی
    max_current = Column(Float, nullable=True)
    cable_type = Column(String(50), nullable=True)
    modbus_address = Column(Integer, nullable=True)  # آدرس Modbus دستگاه

    # داده‌های اضافی
    metadata_info = Column("metadata", JSONB, nullable=True)

    # وضعیت و مانیتورینگ
    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)  # شمارنده خطای تله‌متری
    last_success = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    post = relationship("Post", back_populates="feeders")
    
    # اضافه شدن روابط برای تکمیل Bidirectional (همانند Post)
    timeseries_data = relationship("TimeseriesData", back_populates="feeder", cascade="all, delete-orphan")
    command_logs = relationship("CommandLog", back_populates="feeder")
    device_tests = relationship("DeviceTestLog", back_populates="feeder")

    __table_args__ = (
        Index('idx_feeder_post', 'post_id'),
    )


# =========================================
# مدل لینک
# =========================================

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=True)

    # ارتباط مبدأ و مقصد
    from_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    to_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    # داده‌های استاتیک
    cable_type = Column(String(50), nullable=True)
    cross_section = Column(Float, nullable=True)  # mm²
    length = Column(Float, nullable=True)  # متر
    allowed_current = Column(Float, nullable=True)  # آمپر

    # وضعیت
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    from_post = relationship("Post", foreign_keys=[from_post_id], back_populates="outgoing_links")
    to_post = relationship("Post", foreign_keys=[to_post_id], back_populates="incoming_links")
