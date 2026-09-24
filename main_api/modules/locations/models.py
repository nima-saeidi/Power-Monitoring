from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from main_api.core.database import Base


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
    posts = relationship(
        "Post",
        back_populates="location"
    )
