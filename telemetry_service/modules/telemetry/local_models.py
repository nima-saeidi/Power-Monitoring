from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ایمپورت Base از تنظیمات دیتابیس تله‌متری
from telemetry_service.core.database import Base


class LocalPost(Base):
    """
    مدل سبک برای اتصال به جدول posts.
    فقط برای خواندن IP پست‌ها جهت برقراری ارتباط با فیدرهای زیرمجموعه آن استفاده می‌شود.
    """
    __tablename__ = "posts"

    # فیلدهای ضروری برای سرویس تله‌متری
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # ارتباط با فیدرها (برای Join کردن و واکشی همزمان)
    feeders: Mapped[list["LocalFeeder"]] = relationship("LocalFeeder", back_populates="post")


class LocalFeeder(Base):
    """
    مدل سبک برای اتصال به جدول feeders.
    تله‌متری روی این مدل پیمایش (Iterate) می‌کند و دیتا را بر اساس modbus_address از IP پستِ والد می‌خواند.
    """
    __tablename__ = "feeders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))

    # آدرس مودباس (Slave ID / Unit ID) که برای خواندن دیتای اختصاصی این فیدر ضروری است
    modbus_address: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    # ارتباط با پست والد برای دسترسی به ip_address
    post: Mapped["LocalPost"] = relationship("LocalPost", back_populates="feeders")
