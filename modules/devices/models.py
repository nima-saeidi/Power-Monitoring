from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from core.database import Base


# ۱. تعریف مدل مکان برای ساختار درختی و سلسله‌مراتبی (پردیس‌ها، ساختمان‌ها و ...)
class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location_type = Column(String, nullable=True)  # مثلاً 'University', 'Campus', 'Zone'

    # کلید خارجی به خود جدول برای ایجاد ساختار درختی (والد و فرزند)
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=True)

    # روابط
    children = relationship("Location", backref="parent", remote_side=[id])
    posts = relationship("Post", back_populates="location")


# ۲. به‌روزرسانی مدل پست
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)

    # ارتباط پست با جدول مکان‌ها (جایگزین فیلد متنی قبلی شد)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    transformer_specs = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # روابط
    location = relationship("Location", back_populates="posts")
    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")


# ۳. مدل فیدر (بدون تغییر، شامل مدیریت خطای تله‌متری)
class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    name = Column(String, nullable=False)
    max_current = Column(Float, nullable=True)
    cable_type = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)  # شمارنده خطای تله‌متری

    # روابط
    post = relationship("Post", back_populates="feeders")


# ۴. مدل لینک (بدون تغییر)
class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    # ارتباط با گره مبدأ و مقصد
    from_post_id = Column(Integer, ForeignKey("posts.id"))
    to_post_id = Column(Integer, ForeignKey("posts.id"))

    # داده‌های استاتیک
    cable_type = Column(String)  # نوع کابل
    cross_section = Column(Float)  # سطح مقطع
    allowed_current = Column(Float)  # جریان مجاز

    # روابط (در صورت نیاز به دسترسی به آبجکت پست از طریق لینک)
    from_post = relationship("Post", foreign_keys=[from_post_id])
    to_post = relationship("Post", foreign_keys=[to_post_id])
