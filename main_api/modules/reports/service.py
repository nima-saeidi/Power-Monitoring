# app/reports/service.py
from sqlalchemy.orm import Session
from datetime import datetime
from app.reports.repository import ReportRepository


class ReportService:
    def __init__(self, db: Session):
        self.repository = ReportRepository(db)

    def fetch_feeder_report(self, feeder_id: int, start_date: datetime, end_date: datetime):
        # اعتبارسنجی تاریخ‌ها
        if start_date > end_date:
            raise ValueError("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")

        return self.repository.get_feeder_history(feeder_id, start_date, end_date)

    # ... (کدهای قبلی) ...

    def fetch_alerts_report(self, start_date: datetime, end_date: datetime, post_id: int = None):
        if start_date > end_date:
            raise ValueError("بازه زمانی نامعتبر است.")
        return self.repository.get_alerts_history(start_date, end_date, post_id)

    def fetch_aggregated_report(self, feeder_id: int, parameter_key: str, start_date: datetime, end_date: datetime):
        if start_date > end_date:
            raise ValueError("بازه زمانی نامعتبر است.")

        stats = self.repository.get_aggregated_stats(feeder_id, parameter_key, start_date, end_date)

        # اگر دیتایی یافت نشد
        if stats.avg_value is None:
            raise ValueError("داده‌ای برای این بازه زمانی و پارامتر یافت نشد.")

        return {
            "feeder_id": feeder_id,
            "parameter": parameter_key,
            "avg_value": round(stats.avg_value, 2),
            "max_value": stats.max_value,
            "min_value": stats.min_value,
            "start_date": start_date,
            "end_date": end_date
        }

    def fetch_posts_dashboard_status(self):
        # این بخش می‌تواند با Redis ترکیب شود تا وضعیت Live را برگرداند
        # فعلاً از دیتابیس می‌خوانیم
        return self.repository.get_all_posts_status()
