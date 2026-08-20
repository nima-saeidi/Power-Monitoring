from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from typing import List, Dict, Any

# مسیر ایمپورت‌ها را بر اساس ساختار پروژه خود تنظیم کنید
from main_api.core.database import get_db
from main_api.modules.devices.models import Feeder

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry Worker API"])


@router.get("/active-feeders", response_model=List[Dict[str, Any]])
async def get_active_feeders_for_worker(db: AsyncSession = Depends(get_db)):
    """
    این اندپوینت لیست فیدرهای فعال را برای telemetry_service ارسال می‌کند.
    شامل IP، پورت، آدرس مدباس و رجیسترهای پارامترها (metadata) است.
    """
    try:
        # ایجاد کوئری به روش Async (استفاده از select)
        stmt = (
            select(Feeder)
            .options(joinedload(Feeder.post))
            .filter(Feeder.is_active == True)
        )

        # اجرای کوئری
        result = await db.execute(stmt)
        # به دلیل استفاده از joinedload بهتر است از unique استفاده کنیم تا رکوردهای تکراری برنگردد
        active_feeders = result.unique().scalars().all()

        output = []
        for feeder in active_feeders:
            # ۱. تعیین IP: اگر خود فیدر IP داشت آن را برمی‌داریم، در غیر این صورت IP پست را قرار می‌دهیم
            ip = feeder.ip_address
            if not ip and feeder.post:
                ip = feeder.post.ip_address

            # ۲. تعیین پورت مدباس (از پست می‌خوانیم، پیش‌فرض 502)
            port = feeder.post.port if feeder.post and getattr(feeder.post, 'port', None) else 502

            # اگر هیچ IP برای این فیدر یا پست آن ثبت نشده بود، از آن رد می‌شویم
            if not ip:
                continue

            # اضافه کردن اطلاعات فیدر به لیست خروجی
            output.append({
                "id": feeder.id,
                "name": feeder.name,
                "post_id": feeder.post_id,
                "ip_address": ip,
                "port": port,
                "modbus_address": feeder.modbus_address or 1,  # پیش‌فرض مدباس 1
                "metadata_info": feeder.metadata_info or {}  # رجیسترها برای خواندن مقادیر توسط worker
            })

        return output

    except Exception as e:
        # در صورت بروز خطا در دیتابیس، ارور 500 برمی‌گردانیم
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
