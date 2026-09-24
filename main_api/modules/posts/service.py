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

from main_api.modules.posts.repository import PostRepository
from main_api.modules.posts.schemas import PostCreate, PostUpdate


class PostService:

    def __init__(self, repo: PostRepository, broker: RabbitMQPublisher):
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
    # POST SERVICES
    # =========================================================
    async def create_post(self, data: PostCreate, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        new_post = await self.repo.create_post(data)
        await self._publish("post", "create", data=new_post)

        schedule_audit_log(
            background_tasks, action="CREATE_POST", username=username, success=True, severity="INFO",
            description=f"پست جدید '{getattr(data, 'name', 'نامشخص')}' ایجاد شد."
        )
        return new_post

    async def update_post(self, post_id: int, data: PostUpdate, background_tasks: Optional[BackgroundTasks] = None,
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

        schedule_audit_log(
            background_tasks, action="UPDATE_POST", username=username, success=True, severity="INFO",
            description=f"پست با شناسه {post_id} بروزرسانی شد."
        )
        return updated_post

    async def delete_post(self, post_id: int, background_tasks: Optional[BackgroundTasks] = None, username: Optional[str] = None):
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            asyncio.create_task(send_audit_log(
                action="DELETE_POST_FAILED", username=username, success=False, severity="WARNING",
                description=f"تلاش برای حذف پست ناموجود با شناسه {post_id}."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        await self.repo.delete_post(post)
        await self._publish("post", "delete", data={}, filters={"id": post_id})

        schedule_audit_log(
            background_tasks, action="DELETE_POST", username=username, success=True, severity="WARNING",
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
