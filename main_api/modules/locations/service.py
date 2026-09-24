import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import HTTPException, status, BackgroundTasks

try:
    from main_api.common.message_broker import RabbitMQPublisher
except ImportError:
    from main_api.core.broker import RabbitMQPublisher

from main_api.modules.audit_logs.services import send_audit_log, schedule_audit_log

from main_api.modules.locations.repository import LocationRepository
from main_api.modules.locations.schemas import (
    CampusWithSubsectionsCreate,
    LocationCreate,
    LocationUpdate,
)


class LocationService:

    def __init__(self, repo: LocationRepository, broker: RabbitMQPublisher):
        self.repo = repo
        self.broker = broker

    async def _publish(self, entity: str, action: str, data: dict, filters: Optional[dict] = None):
        """
        A helper method to publish events to RabbitMQ.
        Automatically adds routing_key, event_id, timestamp, and entity name.
        """
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, '_asdict'):
            data_dict = data._asdict()
        elif hasattr(data, '__dict__'):
            data_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
        else:
            data_dict = data

        event_body = {
            "entity": entity,
            "action": action,
            "data": data_dict,
            "filters": filters if filters else {},
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        routing_key = f"{entity}.{action}"
        await self.broker.publish_event(routing_key=routing_key, message=event_body)

    # =========================================================
    # LOCATION SERVICES
    # =========================================================
    async def create_location(self, data: LocationCreate, background_tasks: Optional[BackgroundTasks] = None,
                              username: Optional[str] = None):
        # بررسی وجود والد در صورت ارسال parent_id
        if data.parent_id:
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                asyncio.create_task(send_audit_log(
                    action="CREATE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                    description=f"والد با شناسه {data.parent_id} برای ایجاد مکان جدید یافت نشد."
                ))
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent location with id {data.parent_id} not found."
                )

        new_location_obj = await self.repo.create_location(data)
        # دریافت شیء کامل جهت انتشار رویداد
        full_new_location = await self.repo.get_location_by_id(new_location_obj.id)

        await self._publish("location", "create", data=full_new_location)

        # لاگ موفقیت‌آمیز
        schedule_audit_log(
            background_tasks, action="CREATE_LOCATION", username=username, success=True, severity="INFO",
            description=f"مکان جدید '{getattr(data, 'name', 'نامشخص')}' ایجاد شد."
        )

        return full_new_location

    async def update_location(self, location_id: int, data: LocationUpdate, background_tasks: Optional[BackgroundTasks] = None,
                              username: Optional[str] = None):
        existing_location = await self.repo.get_location_by_id(location_id)
        if not existing_location:
            asyncio.create_task(send_audit_log(
                action="UPDATE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای ویرایش مکان ناموجود با شناسه {location_id}."
            ))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with id {location_id} not found."
            )

        if data.parent_id is not None:
            if data.parent_id == location_id:
                asyncio.create_task(send_audit_log(
                    action="UPDATE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                    description=f"تلاش ناموفق: مکان با شناسه {location_id} نمی‌تواند والد خودش باشد."
                ))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A location cannot be its own parent."
                )
            parent = await self.repo.get_location_by_id(data.parent_id)
            if not parent:
                asyncio.create_task(send_audit_log(
                    action="UPDATE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                    description=f"والد تعیین شده با شناسه {data.parent_id} برای مکان {location_id} یافت نشد."
                ))
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent location with id {data.parent_id} not found."
                )

        updated_location = await self.repo.update_location(location_id, data)
        if not updated_location:
            asyncio.create_task(send_audit_log(
                action="UPDATE_LOCATION_FAILED", username=username, success=False, severity="ERROR",
                description=f"خطای داخلی در بروزرسانی مکان با شناسه {location_id}."
            ))
            raise HTTPException(status_code=404, detail="Location not found")

        update_data = data.model_dump(exclude_unset=True)
        await self._publish("location", "update", data=update_data, filters={"id": location_id})

        schedule_audit_log(
            background_tasks, action="UPDATE_LOCATION", username=username, success=True, severity="INFO",
            description=f"مکان با شناسه {location_id} با موفقیت بروزرسانی شد."
        )

        return updated_location

    async def delete_location(self, location_id: int, background_tasks: Optional[BackgroundTasks] = None,
                              username: Optional[str] = None):
        is_deleted = await self.repo.delete_location(location_id)
        if not is_deleted:
            asyncio.create_task(send_audit_log(
                action="DELETE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف مکان ناموجود با شناسه {location_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

        await self._publish("location", "delete", data={}, filters={"id": location_id})

        schedule_audit_log(
            background_tasks, action="DELETE_LOCATION", username=username, success=True, severity="WARNING",
            description=f"مکان با شناسه {location_id} حذف شد."
        )

        return {"message": "Location deleted successfully."}

    async def get_locations_flat(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_locations_flat(skip=skip, limit=limit)

    async def get_locations(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_locations(skip=skip, limit=limit)

    async def get_location(self, location_id: int):
        location = await self.repo.get_location_by_id(location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        return location

    async def get_posts_by_location(self, location_id: int):
        return await self.repo.get_posts_by_location(location_id)

    # =========================================================
    # CAMPUS / BULK SERVICES
    # =========================================================
    async def create_campus_with_subsections(self, data: CampusWithSubsectionsCreate, background_tasks: Optional[BackgroundTasks] = None,
                                             username: Optional[str] = None):
        try:
            new_campus = await self.repo.create_campus_with_subsections(data)

            # انتشار رویداد برای ایجاد پردیس به همراه تمامی بخش‌های داخلی آن
            await self._publish("campus", "create", data=new_campus)

            background_tasks.add_task(
                send_audit_log, action="CREATE_CAMPUS", username=username, success=True, severity="INFO",
                description=f"پردیس جدید '{getattr(data, 'name', 'نامشخص')}' به همراه زیرمجموعه‌ها ایجاد شد."
            )
            return new_campus
        except Exception as e:
            asyncio.create_task(send_audit_log(
                action="CREATE_CAMPUS_FAILED", username=username, success=False, severity="ERROR",
                description=f"خطا در ایجاد پردیس یکپارچه: {str(e)}"
            ))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create campus with subsections."
            )

    # =========================================================
    # EXPORT SERVICES (Pandas integration for Reporting)
    # =========================================================
    async def export_devices_to_excel(self, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        try:
            # دریافت داده‌ها برای تهیه گزارش (به‌عنوان نمونه)
            locations = await self.repo.get_all_locations(skip=0, limit=10000)

            # پردازش و ساخت دیتافریم با Pandas (صرفاً بخش لاجیک؛ تبدیل نهایی در Router انجام می‌شود)
            data_list = [{"ID": loc.id, "Name": loc.name, "Type": loc.type, "Parent_ID": loc.parent_id} for loc in
                         locations]
            df = pd.DataFrame(data_list)

            schedule_audit_log(
                background_tasks, action="EXPORT_DEVICES_EXCEL", username=username, success=True, severity="INFO",
                description="خروجی اکسل دستگاه‌ها و مکان‌ها با موفقیت ایجاد شد."
            )

            # بازگرداندن داده پردازش شده (عملیات I/O نهایی برای ساخت فایل اکسل می‌تواند در Router یا یک Utility باشد)
            return df
        except Exception as e:
            asyncio.create_task(send_audit_log(
                action="EXPORT_DEVICES_FAILED", username=username, success=False, severity="ERROR",
                description=f"خطا در ایجاد گزارش اکسل: {str(e)}"
            ))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate Excel report."
            )
