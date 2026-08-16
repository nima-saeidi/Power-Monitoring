# app/reports/repository.py
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

# TODO: ایمپورت مدل دیتابیس سری زمانی خود را اینجا قرار دهید
# فرض می‌کنیم مدل شما TimeseriesData نام دارد و در app.devices.models یا app.models است
from main_api.modules.devices.models import TimeseriesData

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_feeder_history(self, feeder_id: int, start_date: datetime, end_date: datetime) -> List[TimeseriesData]:
        return self.db.query(TimeseriesData).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        ).order_by(TimeseriesData.timestamp.asc()).all()


from sqlalchemy import func
# فرض می‌کنیم مدل آلارم و پست را ایمپورت کرده‌اید:
# from app.models import DeviceAlert, Post

    # ... (کدهای قبلی) ...

    # ۱. متد دریافت تاریخچه هشدارها
    def get_alerts_history(self, start_date: datetime, end_date: datetime, post_id: int = None):
        query = self.db.query(DeviceAlert).filter(
            DeviceAlert.created_at >= start_date,
            DeviceAlert.created_at <= end_date
        )
        if post_id:
            query = query.filter(DeviceAlert.post_id == post_id)
        return query.order_by(DeviceAlert.created_at.desc()).all()

    # ۲. متد دریافت گزارش آماری (میانگین، حداکثر و حداقل) برای نمودارها
    def get_aggregated_stats(self, feeder_id: int, parameter_key: str, start_date: datetime, end_date: datetime):
        result = self.db.query(
            func.avg(TimeseriesData.value).label('avg_value'),
            func.max(TimeseriesData.value).label('max_value'),
            func.min(TimeseriesData.value).label('min_value')
        ).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.key == parameter_key,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        ).first()
        return result

    # ۳. متد دریافت وضعیت فعلی تمامی پست‌ها برای داشبورد
    def get_all_posts_status(self):
        # در اینجا می‌توانید منطق محاسبه وضعیت آنلاین/آفلاین بودن را بر اساس آخرین دیتای ارسالی پیاده‌سازی کنید
        return self.db.query(Post).all()
