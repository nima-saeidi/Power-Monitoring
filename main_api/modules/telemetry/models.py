from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from main_api.core.database import Base

# 🔴 قدم اول (بسیار مهم):
# برای رفع خطای پیدا نشدن جدول، باید مدل فیدر را در اینجا ایمپورت کنید تا دیتابیس آن را بشناسد.
# (مسیر ایمپورت زیر را بر اساس پوشه‌بندی پروژه خودتان از کامنت خارج و اصلاح کنید):
from main_api.modules.devices.models import Feeder


class TimeseriesData(Base):
    __tablename__ = "timeseries_data"
    __table_args__ = {'extend_existing': True}

    # ۱. شناسه رکورد
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ۲. شناسه فیدر (کلید خارجی) - 👈 با سینتکس Mapped یکپارچه شد
    # ⚠️ قدم دوم: فایل مدل فیدر را چک کنید. اگر متغیر __tablename__ برابر "feeders" (با s) است،
    # عبارت "feeder.id" در خط زیر را به "feeders.id" تغییر دهید.
    feeder_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("feeders.id"))

    # ۳. کلید یا نام پارامتر
    key: Mapped[str] = mapped_column(String, index=True)

    # ۴. مقدار اعشاری
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ۵. شناسه پست و مقدار صحیح
    post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_int: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ۶. زمان
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # در صورت نیاز به رلیشن‌ها (از کامنت خارج کنید)
    # feeder = relationship("Feeder", back_populates="timeseries_data")
