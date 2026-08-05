from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from core.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location = Column(String, nullable=True) 
    transformer_specs = Column(String, nullable=True) 
    ip_address = Column(String, nullable=True) 
    is_active = Column(Boolean, default=True) 

    feeders = relationship("Feeder", back_populates="post", cascade="all, delete-orphan")

class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    name = Column(String, nullable=False)
    max_current = Column(Float, nullable=True) 
    cable_type = Column(String, nullable=True) 
    is_active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)
    post = relationship("Post", back_populates="feeders")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    
    # ارتباط با گره مبدأ و مقصد
    from_post_id = Column(Integer, ForeignKey("posts.id"))
    to_post_id = Column(Integer, ForeignKey("posts.id"))
    
    # داده‌های استاتیک
    cable_type = Column(String) # نوع کابل
    cross_section = Column(Float) # سطح مقطع
    allowed_current = Column(Float) # جریان مجاز
    
    # روابط (در صورت نیاز به دسترسی به آبجکت پست از طریق لینک)
    from_post = relationship("Post", foreign_keys=[from_post_id])
    to_post = relationship("Post", foreign_keys=[to_post_id])