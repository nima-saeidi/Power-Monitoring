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

# =========================================
# مدل مکان برای ساختار درختی
# =========================================
class Location(Base):

    __tablename__ = "locations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        index=True,
        nullable=False
    )

    location_type = Column(
        String(50),
        nullable=True
    )

    description = Column(
        Text,
        nullable=True
    )

    parent_id = Column(
        Integer,
        ForeignKey(
            "locations.id",
            ondelete="CASCADE"
        ),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ========================================================
    # SELF RELATIONSHIP
    # ========================================================

    children = relationship(
        "Location",
        back_populates="parent",
        lazy="selectin",  # <--- این بخش اضافه شود
        cascade="all, delete-orphan"
    )

    parent = relationship(
        "Location",
        back_populates="children",
        remote_side="[Location.id]",
        lazy="selectin"  # <--- این بخش اضافه شود
    )

    # ========================================================
    # POSTS
    # ========================================================

    posts = relationship(
        "Post",
        foreign_keys="[Post.location_id]",
        back_populates="location"
    )

    campus_posts = relationship(
        "Post",
        foreign_keys="[Post.campus_id]",
        back_populates="campus"
    )

    unit_posts = relationship(
        "Post",
        foreign_keys="[Post.unit_id]",
        back_populates="unit"
    )


# =========================================
# مدل پست
# =========================================
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)

    # --- فیلدهای اضافه شده بر اساس مرحله ۱ (اطلاعات پایه) ---
    supply_source = Column(String(150), nullable=True)  # محل تغذیه
    campus_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)  # پردیس
    unit_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)  # واحد

    # موقعیت کلی سلسله مراتبی (می‌تواند همان واحد یا سطح پایین‌تر باشد)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    transformer_specs = Column(String(200), nullable=True)  # مشخصات جریان
    ip_address = Column(String(45), nullable=True, unique=True)
    port = Column(Integer, default=502)

    # --- فیلدهای اضافه شده بر اساس مرحله ۳ (موقعیت مکانی روی نقشه) ---
    latitude = Column(Float, nullable=True)  # عرض جغرافیایی
    longitude = Column(Float, nullable=True)  # طول جغرافیایی

    metadata_info = Column("metadata", JSONB, nullable=True)  # برای فیلدهای سفارشی ۱ و ۲
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    location = relationship("Location", foreign_keys=[location_id], back_populates="posts")
    campus = relationship("Location", foreign_keys=[campus_id], back_populates="campus_posts")
    unit = relationship("Location", foreign_keys=[unit_id], back_populates="unit_posts")

    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")
    command_logs = relationship("CommandLog", back_populates="post")
    device_tests = relationship("DeviceTestLog", back_populates="post")

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

    # --- فیلد اضافه شده بر اساس مرحله ۲ (تعریف فیدر) ---
    feeder_type = Column(String(50), nullable=True)  # نوع فیدر: تولید کننده / مصرف کننده

    max_current = Column(Float, nullable=True)  # حداکثر جریان (A)
    cable_type = Column(String(50), nullable=True)
    modbus_address = Column(Integer, nullable=True)

    # اطلاعات دینامیک (IP و رجیستر پارامترها مانند توان اکتیو، ولتاژ و...) در این فیلد JSON ذخیره می‌شوند
    metadata_info = Column("metadata", JSONB, nullable=True)

    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="feeders")
    command_logs = relationship("CommandLog", back_populates="feeder")
    device_tests = relationship("DeviceTestLog", back_populates="feeder")

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

    # --- مرحله ۱: انتخاب پست‌ها ---
    from_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    to_post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    # --- مرحله ۲: اطلاعات ثابت لینک ---
    cable_type = Column(String(50), nullable=True)  # نوع سیم
    cross_section = Column(Float, nullable=True)  # سطح مقطع
    allowed_current = Column(Float, nullable=True)  # جریان مجاز (A)
    length = Column(Float, nullable=True)  # طول لینک (اختیاری)

    # --- مرحله ۳: اطلاعات دینامیک لینک ---
    # برای ذخیره تنظیمات و رجیسترهای مربوط به جریان، توان اکتیو و توان راکتیو
    metadata_info = Column("metadata", JSONB, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # روابط
    from_post = relationship("Post", foreign_keys=[from_post_id], back_populates="outgoing_links")
    to_post = relationship("Post", foreign_keys=[to_post_id], back_populates="incoming_links")