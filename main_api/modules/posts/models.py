from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base


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
