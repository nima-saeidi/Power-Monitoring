# logging_service/modules/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from core.database import Base

class AuditLog(Base):
    # نکته‌ی مهم: این سرویس (طبق تنظیمات docker-compose) عملاً از همان دیتابیس
    # power_monitoring که main_api استفاده می‌کند استفاده می‌کند (چون DATABASE_URL
    # مشترک از .env ریشه تزریق می‌شود و دیتابیس جداگانه‌ی power_logs هرگز ساخته
    # نمی‌شود). main_api از قبل (از طریق Alembic) جدولی به نام audit_logs با
    # ساختار کاملاً متفاوتی دارد؛ اگر این مدل هم از همان نام استفاده می‌کرد،
    # Base.metadata.create_all() آن جدول قدیمی را «موجود» تشخیص می‌داد و هرگز
    # نمی‌ساخت، و insert کردن این سرویس با خطای «ستون وجود ندارد» شکست می‌خورد.
    # به همین دلیل نام جدول این سرویس عمداً متفاوت انتخاب شده است.
    __tablename__ = "service_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_name = Column(String(50), nullable=True, index=True)      # مثلا main_api
    action = Column(String(100), nullable=False, index=True)         # نوع عملیات
    user_id = Column(Integer, nullable=True, index=True)             # آیدی کاربری که درخواست زده
    details = Column(JSONB, nullable=True)                           # کل اطلاعات متغیر لاگ (Body، پاسخ و...)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
