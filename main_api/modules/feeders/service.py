import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Union

from fastapi import HTTPException, status, BackgroundTasks

try:
    from main_api.common.message_broker import RabbitMQPublisher
except ImportError:
    from main_api.core.broker import RabbitMQPublisher

from main_api.modules.audit_logs.services import send_audit_log, schedule_audit_log

from main_api.modules.feeders.excel_import import import_hierarchy
from main_api.modules.feeders.repository import FeederRepository
from main_api.modules.feeders.schemas import FeederCreate, FeederUpdate
from main_api.modules.telemetry.live import live_monitor


class FeederService:

    def __init__(self, repo: FeederRepository, broker: RabbitMQPublisher):
        self.repo = repo
        self.broker = broker

    async def _publish(self, entity: str, action: str, data: dict, filters: Optional[dict] = None):
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

    async def create_feeders(self, data_input: Union[List[FeederCreate], FeederCreate],
                             background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        if not isinstance(data_input, list):
            data_list = [data_input]
        else:
            data_list = data_input

        created_feeders = []
        for data in data_list:
            new_feeder = await self.repo.create_feeder(data)
            await self._publish("feeder", "create", data=new_feeder)
            live_monitor.invalidate()
            created_feeders.append(new_feeder)

        schedule_audit_log(
            background_tasks, action="CREATE_FEEDERS", username=username, success=True, severity="INFO",
            description=f"تعداد {len(data_list)} فیدر جدید با موفقیت ایجاد شد."
        )

        return created_feeders[0] if not isinstance(data_input, list) else created_feeders

    async def update_feeder(self, feeder_id: int, data: FeederUpdate, background_tasks: Optional[BackgroundTasks] = None,
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
        live_monitor.invalidate()

        schedule_audit_log(
            background_tasks, action="UPDATE_FEEDER", username=username, success=True, severity="INFO",
            description=f"فیدر با شناسه {feeder_id} بروزرسانی شد."
        )
        return updated_feeder

    async def delete_feeder(self, feeder_id: int, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            asyncio.create_task(send_audit_log(
                action="DELETE_FEEDER_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف فیدر ناموجود با شناسه {feeder_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")

        await self.repo.delete_feeder(feeder)
        await self._publish("feeder", "delete", data={}, filters={"id": feeder_id})
        live_monitor.invalidate()

        schedule_audit_log(
            background_tasks, action="DELETE_FEEDER", username=username, success=True, severity="WARNING",
            description=f"فیدر با شناسه {feeder_id} حذف شد."
        )
        return {"message": "Feeder deleted successfully."}

    async def get_feeders(self, post_id: Optional[int] = None, skip: int = 0, limit: int = 100, **filters):
        return await self.repo.get_all_feeders(post_id=post_id, skip=skip, limit=limit, **filters)

    async def get_feeder(self, feeder_id: int):
        feeder = await self.repo.get_feeder_by_id(feeder_id)
        if not feeder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeder not found.")
        return feeder

    async def import_feeders_from_excel(self, df, background_tasks: Optional[BackgroundTasks] = None,
                                        username: Optional[str] = None):
        stats = await import_hierarchy(self.repo.db, df)
        live_monitor.invalidate()
        schedule_audit_log(
            background_tasks, action="IMPORT_FEEDERS_EXCEL", username=username, success=True, severity="INFO",
            description=(f"ورود اکسل: {stats['rows']} ردیف، {stats['posts_created']} پست و "
                         f"{stats['feeders_created']} فیدر جدید، {stats['feeders_updated']} فیدر به‌روزرسانی شد.")
        )
        return stats
