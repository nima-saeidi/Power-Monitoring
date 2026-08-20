# app/reports/repository.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional

# مسیرها را در صورت نیاز با پروژه خود تطبیق دهید
from main_api.modules.devices.models import TimeseriesData, Post


# from main_api.modules.alerts.models import Alert # (فرض بر این است که مدلی برای آلارم دارید)

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_feeder_history(self, feeder_id: int, start_date: datetime, end_date: datetime) -> List[TimeseriesData]:
        return self.db.query(TimeseriesData).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        ).order_by(TimeseriesData.timestamp.asc()).all()

    # ۲. متد دریافت گزارش آماری (میانگین، حداکثر و حداقل) برای نمودارها
    def get_aggregated_stats(self, feeder_id: int, parameter_key: str, start_date: datetime, end_date: datetime):
        # از value_int استفاده می‌کنیم چون داده‌های مدباس شما عدد صحیح/اعشاری هستند
        result = self.db.query(
            func.avg(TimeseriesData.value_int).label('avg_value'),
            func.max(TimeseriesData.value_int).label('max_value'),
            func.min(TimeseriesData.value_int).label('min_value')
        ).filter(
            TimeseriesData.feeder_id == feeder_id,
            TimeseriesData.key == parameter_key,
            TimeseriesData.timestamp >= start_date,
            TimeseriesData.timestamp <= end_date
        ).first()
        return result

    # ۳. متد دریافت وضعیت فعلی تمامی پست‌ها برای داشبورد
    def get_all_posts_status(self):
        return self.db.query(Post).all()

    # ۴. متدی که در سرویس فراخوانی شده بود اما وجود نداشت
    def get_alerts_history(self, start_date: datetime, end_date: datetime, post_id: Optional[int] = None):
        # منطق واقعی آلارم را اینجا پیاده کنید (زمانی که مدل Alert را ساختید)
        # query = self.db.query(Alert).filter(Alert.created_at >= start_date, Alert.created_at <= end_date)
        # if post_id:
        #     query = query.filter(Alert.post_id == post_id)
        # return query.all()
        return []  # فعلاً لیست خالی برمی‌گرداند تا خطا ندهد
