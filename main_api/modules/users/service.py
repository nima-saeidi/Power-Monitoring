import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.security import hash_password
from main_api.modules.users.repository import UserRepository
from main_api.modules.users.schemas import UserResponse, UserCreate, UserUpdate
from main_api.core.broker import RabbitMQPublisher

# ایمپورت تابع ارسال لاگ
from main_api.modules.audit_logs.services import send_audit_log, schedule_audit_log


class UserService:
    """مدیریت کاربران (CRUD) توسط ادمین. برای عملیات احراز هویت/رمز عبور به AuthService مراجعه کنید."""

    def __init__(self, repository: UserRepository, publisher: RabbitMQPublisher, db: AsyncSession):
        self.repo = repository
        self.publisher = publisher
        self.db = db
        self.db_routing_key = "db.users.write"

    async def _publish(self, payload: dict):
        """ارسال رویدادهای استاندارد تغییر وضعیت کاربر به صف RabbitMQ (CQRS)"""
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "entity": payload.get("entity", "user"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload
        }
        await self.publisher.publish_event(
            routing_key=self.db_routing_key,
            message=event_payload
        )

    async def get_all_users(self) -> list[UserResponse]:
        users = await self.repo.get_all()
        return [UserResponse.model_validate(u) for u in users]

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        return UserResponse.model_validate(user)

    async def create_user(self, data: UserCreate, background_tasks: Optional[BackgroundTasks] = None, current_user: UserResponse = None):
        if await self.repo.get_by_email(data.email):
            raise HTTPException(status_code=400, detail="این ایمیل قبلاً ثبت شده است.")
        if data.phone_number and await self.repo.get_by_phone_number(data.phone_number):
            raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت شده است.")

        await self._publish({
            "entity": "user",
            "action": "CREATE_USER",
            "data": {
                "name": data.name,
                "email": data.email,
                "phone_number": data.phone_number,
                "hashed_password": hash_password(data.password),
                "role": data.role,
                "is_active": data.is_active,
                "sms_notification_enabled": data.sms_notification_enabled
            }
        })

        actor_id = current_user.id if current_user else None
        actor_name = current_user.email if current_user else None

        schedule_audit_log(
            background_tasks, action="CREATE_USER_QUEUED", user_id=actor_id, username=actor_name,
            success=True, severity="INFO", description=f"درخواست ایجاد کاربر {data.email} در صف قرار گرفت"
        )
        return {"status": "accepted", "message": "درخواست ایجاد کاربر در صف پردازش قرار گرفت."}

    async def update_user(self, user_id: int, data: UserUpdate, background_tasks: Optional[BackgroundTasks] = None,
                          current_user: UserResponse = None):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        if update_data:
            await self._publish({
                "entity": "user",
                "action": "UPDATE_USER",
                "user_id": user_id,
                "data": update_data
            })

            actor_id = current_user.id if current_user else user_id
            actor_name = current_user.email if current_user else user.email

            schedule_audit_log(
                background_tasks, action="UPDATE_USER_QUEUED", user_id=actor_id, username=actor_name,
                success=True, severity="INFO", description=f"بروزرسانی اطلاعات کاربر با ID {user_id}"
            )
        return {"status": "accepted", "message": "درخواست بروزرسانی کاربر در صف قرار گرفت."}

    async def delete_user(self, user_id: int, background_tasks: Optional[BackgroundTasks] = None, current_user: UserResponse = None):
        user_to_delete = await self.repo.get_by_id(user_id)
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        await self._publish({
            "entity": "user",
            "action": "DELETE_USER",
            "user_id": user_id
        })

        actor_id = current_user.id if current_user else None
        actor_name = current_user.email if current_user else None

        schedule_audit_log(
            background_tasks, action="DELETE_USER_QUEUED", user_id=actor_id, username=actor_name,
            success=True, severity="CRITICAL", description=f"کاربر با ID {user_id} حذف شد"
        )
        return {"status": "accepted", "message": "درخواست حذف کاربر در صف قرار گرفت."}
