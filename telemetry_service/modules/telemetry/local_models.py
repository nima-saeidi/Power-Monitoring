from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

# ایمپورت Base از تنظیمات دیتابیس تله‌متری
from telemetry_service.core.database import Base

class LocalPost(Base):
    """
    مدل سبک برای اتصال به جدول posts.
    مدیریت اصلی این جدول (ساخت، ویرایش اطلاعات پایه) بر عهده سرویس اصلی است.
    سرویس تله‌متری فقط از این مدل برای خواندن IP و وضعیت تجهیزات استفاده می‌کند.
    """
    __tablename__ = "posts"

    # فیلدهای ضروری برای سرویس تله‌متری
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # نکته: نیازی به تعریف relationship برگشتی (back_populates) به TimeseriesData
    # در اینجا نیست تا از پیچیدگی و وابستگی حلقوی (Circular Import) جلوگیری شود.
