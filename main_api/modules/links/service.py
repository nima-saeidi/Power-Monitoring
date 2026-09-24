import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status, BackgroundTasks

try:
    from main_api.common.message_broker import RabbitMQPublisher
except ImportError:
    from main_api.core.broker import RabbitMQPublisher

from main_api.modules.audit_logs.services import send_audit_log, schedule_audit_log

from main_api.modules.links.repository import LinkRepository
from main_api.modules.links.schemas import LinkCreate, LinkUpdate


class LinkService:

    def __init__(self, repo: LinkRepository, broker: RabbitMQPublisher):
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
    # LINK SERVICES
    # =========================================================
    async def create_link(self, data: LinkCreate, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        new_link = await self.repo.create_link(data)
        await self._publish("link", "create", data=new_link)

        schedule_audit_log(
            background_tasks, action="CREATE_LINK", username=username, success=True, severity="INFO",
            description=f"لینک ارتباطی جدید از نوع '{getattr(data, 'type', 'نامشخص')}' ایجاد شد."
        )
        return new_link

    async def update_link(self, link_id: int, data: LinkUpdate, background_tasks: Optional[BackgroundTasks] = None,
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

        schedule_audit_log(
            background_tasks, action="UPDATE_LINK", username=username, success=True, severity="INFO",
            description=f"لینک ارتباطی با شناسه {link_id} بروزرسانی شد."
        )
        return updated_link

    async def delete_link(self, link_id: int, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        link = await self.repo.get_link_by_id(link_id)
        if not link:
            asyncio.create_task(send_audit_log(
                action="DELETE_LINK_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف لینک ناموجود با شناسه {link_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found.")

        await self.repo.delete_link(link)
        await self._publish("link", "delete", data={}, filters={"id": link_id})

        schedule_audit_log(
            background_tasks, action="DELETE_LINK", username=username, success=True, severity="WARNING",
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
