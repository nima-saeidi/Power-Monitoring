import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Union

import pandas as pd
from fastapi import HTTPException, status, BackgroundTasks

# ایمپورت RabbitMQPublisher (با مسیردهی استاندارد پروژه)
try:
    from main_api.common.message_broker import RabbitMQPublisher
except ImportError:
    from main_api.core.broker import RabbitMQPublisher

# ایمپورت سیستم لاگینگ متمرکز
from main_api.modules.audit_logs.services import send_audit_log

from main_api.modules.devices.repository import DeviceRepository
from main_api.modules.devices.schemas import (
    CampusWithSubsectionsCreate,
    CommandRequest,
    FeederCreate,
    FeederUpdate,
    LinkCreate,
    LinkUpdate,
    LocationCreate,
    LocationUpdate,
    PostCreate,
    PostUpdate,
)


class DeviceService:

    def __init__(self, repo: DeviceRepository, broker: RabbitMQPublisher):
        """
        DeviceService requires a MessageBroker instance for publishing events.
        """
        self.repo = repo
        self.broker = broker

    async def _publish(self, entity: str, action: str, data: dict, filters: Optional[dict] = None):
        """
        A helper method to publish events to RabbitMQ.
        Automatically adds routing_key, event_id, timestamp, and entity name.
        """
        # Pydantic models have .model_dump(), SQLAlchemy objects don't.
        # This safely converts any object to a dictionary.
        if hasattr(data, 'model_dump'):
            data_dict = data.model_dump()
        elif hasattr(data, '_asdict'):  # for SQLAlchemy results / namedtuples
            data_dict = data._asdict()
        elif hasattr(data, '__dict__'):  # for SQLAlchemy ORM objects
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

        # ساخت روتینگ کی استاندارد بر اساس entity و action (مثلاً: location.create)
        routing_key = f"{entity}.{action}"

        # ارسال routing_key اجباری به همراه پیام
        await self.broker.publish_event(routing_key=routing_key, message=event_body)

    # =========================================================
    # LOCATION SERVICES
    # =========================================================
    async def create_location(self, data: LocationCreate, background_tasks: BackgroundTasks,
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
        background_tasks.add_task(
            send_audit_log, action="CREATE_LOCATION", username=username, success=True, severity="INFO",
            description=f"مکان جدید '{getattr(data, 'name', 'نامشخص')}' ایجاد شد."
        )

        return full_new_location

    async def update_location(self, location_id: int, data: LocationUpdate, background_tasks: BackgroundTasks,
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

        background_tasks.add_task(
            send_audit_log, action="UPDATE_LOCATION", username=username, success=True, severity="INFO",
            description=f"مکان با شناسه {location_id} با موفقیت بروزرسانی شد."
        )

        return updated_location

    async def delete_location(self, location_id: int, background_tasks: BackgroundTasks,
                              username: Optional[str] = None):
        is_deleted = await self.repo.delete_location(location_id)
        if not is_deleted:
            asyncio.create_task(send_audit_log(
                action="DELETE_LOCATION_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف مکان ناموجود با شناسه {location_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

        await self._publish("location", "delete", data={}, filters={"id": location_id})

        background_tasks.add_task(
            send_audit_log, action="DELETE_LOCATION", username=username, success=True, severity="WARNING",
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

    # =========================================================
    # POST SERVICES
    # =========================================================
    async def create_post(self, data: PostCreate, background_tasks: BackgroundTasks, username: Optional[str] = None):
        new_post = await self.repo.create_post(data)
        await self._publish("post", "create", data=new_post)

        background_tasks.add_task(
            send_audit_log, action="CREATE_POST", username=username, success=True, severity="INFO",
            description=f"پست جدید '{getattr(data, 'name', 'نامشخص')}' ایجاد شد."
        )
        return new_post

    async def update_post(self, post_id: int, data: PostUpdate, background_tasks: BackgroundTasks,
                          username: Optional[str] = None):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            asyncio.create_task(send_audit_log(
                action="UPDATE_POST_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای ویرایش پست ناموجود با شناسه {post_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        updated_post = await self.repo.update_post(post, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("post", "update", data=update_data, filters={"id": post_id})

        background_tasks.add_task(
            send_audit_log, action="UPDATE_POST", username=username, success=True, severity="INFO",
            description=f"پست با شناسه {post_id} بروزرسانی شد."
        )
        return updated_post

    async def delete_post(self, post_id: int, background_tasks: BackgroundTasks, username: Optional[str] = None):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            asyncio.create_task(send_audit_log(
                action="DELETE_POST_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف پست ناموجود با شناسه {post_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        await self.repo.delete_post(post)
        await self._publish("post", "delete", data={}, filters={"id": post_id})

        background_tasks.add_task(
            send_audit_log, action="DELETE_POST", username=username, success=True, severity="WARNING",
            description=f"پست با شناسه {post_id} حذف شد."
        )
        return {"message": "Post deleted successfully."}

    async def get_posts(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_posts(skip=skip, limit=limit)

    async def get_post(self, post_id: int):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
        return post

    # =========================================================
    # FEEDER SERVICES
    # =========================================================
    async def create_feeders(self, data_input: Union[List[FeederCreate], FeederCreate],
                             background_tasks: BackgroundTasks, username: Optional[str] = None):
        if not isinstance(data_input, list):
            data_list = [data_input]
        else:
            data_list = data_input

        created_feeders = []
        for data in data_list:
            new_feeder = await self.repo.create_feeder(data)
            await self._publish("feeder", "create", data=new_feeder)
            created_feeders.append(new_feeder)

        background_tasks.add_task(
            send_audit_log, action="CREATE_FEEDERS", username=username, success=True, severity="INFO",
            description=f"تعداد {len(data_list)} فیدر جدید با موفقیت ایجاد شد."
        )

        return created_feeders[0] if not isinstance(data_input, list) else created_feeders

    async def update_feeder(self, feeder_id: int, data: FeederUpdate, background_tasks: BackgroundTasks,
                            username: Optional[str] = None):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            asyncio.create_task(send_audit_log(
                action="UPDATE_FEEDER_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای ویرایش فیدر ناموجود با شناسه {feeder_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")

        updated_feeder = await self.repo.update_feeder(feeder, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("feeder", "update", data=update_data, filters={"id": feeder_id})

        background_tasks.add_task(
            send_audit_log, action="UPDATE_FEEDER", username=username, success=True, severity="INFO",
            description=f"فیدر با شناسه {feeder_id} بروزرسانی شد."
        )
        return updated_feeder

    async def delete_feeder(self, feeder_id: int, background_tasks: BackgroundTasks, username: Optional[str] = None):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            asyncio.create_task(send_audit_log(
                action="DELETE_FEEDER_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف فیدر ناموجود با شناسه {feeder_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")

        await self.repo.delete_feeder(feeder)
        await self._publish("feeder", "delete", data={}, filters={"id": feeder_id})

        background_tasks.add_task(
            send_audit_log, action="DELETE_FEEDER", username=username, success=True, severity="WARNING",
            description=f"فیدر با شناسه {feeder_id} حذف شد."
        )
        return {"message": "Feeder deleted successfully."}

    async def get_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_feeders(post_id=post_id, skip=skip, limit=limit)

    async def get_feeder(self, feeder_id: int):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")
        return feeder

    # =========================================================
    # LINK SERVICES
    # =========================================================
    async def create_link(self, data: LinkCreate, background_tasks: BackgroundTasks, username: Optional[str] = None):
        new_link = await self.repo.create_link(data)
        await self._publish("link", "create", data=new_link)

        background_tasks.add_task(
            send_audit_log, action="CREATE_LINK", username=username, success=True, severity="INFO",
            description=f"لینک ارتباطی جدید از نوع '{getattr(data, 'type', 'نامشخص')}' ایجاد شد."
        )
        return new_link

    async def update_link(self, link_id: int, data: LinkUpdate, background_tasks: BackgroundTasks,
                          username: Optional[str] = None):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            asyncio.create_task(send_audit_log(
                action="UPDATE_LINK_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای ویرایش لینک ناموجود با شناسه {link_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

        updated_link = await self.repo.update_link(link, data)
        update_data = data.model_dump(exclude_unset=True)
        await self._publish("link", "update", data=update_data, filters={"id": link_id})

        background_tasks.add_task(
            send_audit_log, action="UPDATE_LINK", username=username, success=True, severity="INFO",
            description=f"لینک ارتباطی با شناسه {link_id} بروزرسانی شد."
        )
        return updated_link

    async def delete_link(self, link_id: int, background_tasks: BackgroundTasks, username: Optional[str] = None):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            asyncio.create_task(send_audit_log(
                action="DELETE_LINK_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف لینک ناموجود با شناسه {link_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

        await self.repo.delete_link(link)
        await self._publish("link", "delete", data={}, filters={"id": link_id})

        background_tasks.add_task(
            send_audit_log, action="DELETE_LINK", username=username, success=True, severity="WARNING",
            description=f"لینک ارتباطی با شناسه {link_id} حذف شد."
        )
        return {"message": "Link deleted successfully."}

    async def get_links(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all_links(skip=skip, limit=limit)

    async def get_link(self, link_id: int):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")
        return link

    # =========================================================
    # CAMPUS / BULK SERVICES
    # =========================================================
    async def create_campus_with_subsections(self, data: CampusWithSubsectionsCreate, background_tasks: BackgroundTasks,
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
    # COMMAND SERVICES (IoT Actions)
    # =========================================================
    async def execute_command(self, data: CommandRequest, background_tasks: BackgroundTasks,
                              username: Optional[str] = None):
        try:
            # ارسال فرمان اجرایی به دیوایس‌های لبه (Edge Devices) از طریق رابیت‌ام‌کیو
            await self._publish("device", "command_execute", data=data)

            background_tasks.add_task(
                send_audit_log, action="EXECUTE_COMMAND", username=username, success=True, severity="WARNING",
                description=f"فرمان کنترلی '{getattr(data, 'command_type', 'نامشخص')}' برای دستگاه صادر شد."
            )
            return {"message": "Command issued successfully.", "status": "pending_execution"}
        except Exception as e:
            asyncio.create_task(send_audit_log(
                action="EXECUTE_COMMAND_FAILED", username=username, success=False, severity="ERROR",
                description=f"خطا در صدور فرمان کنترلی: {str(e)}"
            ))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to issue command to device."
            )

    # =========================================================
    # EXPORT SERVICES (Pandas integration for Reporting)
    # =========================================================
    async def export_devices_to_excel(self, background_tasks: BackgroundTasks, username: Optional[str] = None):
        try:
            # دریافت داده‌ها برای تهیه گزارش (به‌عنوان نمونه)
            locations = await self.repo.get_all_locations(skip=0, limit=10000)

            # پردازش و ساخت دیتافریم با Pandas (صرفاً بخش لاجیک؛ تبدیل نهایی در Router انجام می‌شود)
            data_list = [{"ID": loc.id, "Name": loc.name, "Type": loc.type, "Parent_ID": loc.parent_id} for loc in
                         locations]
            df = pd.DataFrame(data_list)

            background_tasks.add_task(
                send_audit_log, action="EXPORT_DEVICES_EXCEL", username=username, success=True, severity="INFO",
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
