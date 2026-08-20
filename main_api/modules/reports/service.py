# app/reports/service.py
from sqlalchemy.orm import Session
from datetime import datetime
from .repository import ReportRepository  # ایمپورت اصلاح شد

class ReportService:
    def __init__(self, db: Session):
        self.repository = ReportRepository(db)

    def fetch_feeder_report(self, feeder_id: int, start_date: datetime, end_date: datetime):
        if start_date > end_date:
            raise ValueError("تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")
        return self.repository.get_feeder_history(feeder_id, start_date, end_date)

    def fetch_alerts_report(self, start_date: datetime, end_date: datetime, post_id: int = None):
        if start_date > end_date:
            raise ValueError("بازه زمانی نامعتبر است.")
        return self.repository.get_alerts_history(start_date, end_date, post_id)

    def fetch_aggregated_report(self, feeder_id: int, parameter_key: str, start_date: datetime, end_date: datetime):
        if start_date > end_date:
            raise ValueError("بازه زمانی نامعتبر است.")

        stats = self.repository.get_aggregated_stats(feeder_id, parameter_key, start_date, end_date)

        # اگر دیتایی یافت نشد
        if not stats or stats.avg_value is None:
            raise ValueError("داده‌ای برای این بازه زمانی و پارامتر یافت نشد.")

        return {
            "feeder_id": feeder_id,
            "parameter": parameter_key,
            "avg_value": round(stats.avg_value, 2),
            "max_value": round(stats.max_value, 2) if stats.max_value is not None else None,
            "min_value": round(stats.min_value, 2) if stats.min_value is not None else None,
            "start_date": start_date,
            "end_date": end_date
        }

    def fetch_posts_dashboard_status(self):
        return self.repository.get_all_posts_status()
