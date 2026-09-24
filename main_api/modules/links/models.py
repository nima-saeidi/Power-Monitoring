from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base


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
