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

    post = relationship("Post", back_populates="feeders")
