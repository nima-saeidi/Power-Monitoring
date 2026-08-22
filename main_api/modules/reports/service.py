# app/reports/service.py
from sqlalchemy.future import select

# مدل‌های خودتان را ایمپورت کنید (مثلا Telemetry, Post, Alert)

class ReportService:
    def __init__(self, db):
        self.db = db

    # 1. متد گزارش فیدر (اصلاح شده)
    async def fetch_feeder_report(self, feeder_id, start_date, end_date):
        stmt = select(Telemetry).filter(
            Telemetry.feeder_id == feeder_id,
            Telemetry.timestamp >= start_date,
            Telemetry.timestamp <= end_date
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # 2. متد داشبورد پست‌ها
    async def fetch_posts_dashboard_status(self):
        # قبلا اینطور بوده: self.db.query(Post).all()
        stmt = select(Post)  # نام مدل پست خود را قرار دهید
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # 3. متد هشدارها
    async def fetch_alerts_report(self, start_date, end_date, post_id):
        # قبلا اینطور بوده: query = self.db.query(Alert)...
        stmt = select(Alert).filter(
            Alert.timestamp >= start_date,
            Alert.timestamp <= end_date
        )
        if post_id:
            stmt = stmt.filter(Alert.post_id == post_id)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    # 4. متد تجمیعی (Analytics)
    async def fetch_aggregated_report(self, feeder_id, parameter_key, start_date, end_date):
        # هر جا self.db.query داشتید به این شکل تبدیل کنید:
        stmt = select(Telemetry).filter(
            Telemetry.feeder_id == feeder_id,
            Telemetry.timestamp >= start_date,
            Telemetry.timestamp <= end_date
            # احتمالا شرط‌های دیگری هم دارید...
        )
        result = await self.db.execute(stmt)

        # اگر فقط دیتا را برمی‌گردانید:
        data = result.scalars().all()

        # سپس محاسبات تجمیعی خود را روی data انجام دهید...
        return data
