# modules/telemetry/models.py
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class Telemetry(Base):
    __tablename__ = "telemetry_data"

    id = Column(Integer, primary_key=True, index=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id"), index=True)
    
    # ویژگی‌های داینامیک (مقادیر دریافتی از دستگاه)
    active_power = Column(Float, nullable=False)   # توان Active
    reactive_power = Column(Float, nullable=False) # توان Reactive
    voltage = Column(Float, nullable=False)        # ولتاژ
    current = Column(Float, nullable=False)        # جریان
    power_factor = Column(Float, nullable=True)    # ضریب توان
    
    timestamp = Column(DateTime, default=datetime.utcnow) # زمان ثبت داده

    feeder = relationship("Feeder", back_populates="telemetries")
