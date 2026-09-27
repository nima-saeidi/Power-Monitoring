from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from main_api.modules.users.models import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str):
        result = await self.db.execute(select(User).where(User.email == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str):
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int):
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all(self):
        result = await self.db.execute(select(User))
        return result.scalars().all()

    async def get_notification_enabled_emails(self) -> list[str]:
        result = await self.db.execute(
            select(User.email).where(
                User.sms_notification_enabled == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
            )
        )
        return [row[0] for row in result.all()]

    async def update_login_state(
        self, user: User, failed_attempts: int, locked_until: Optional[datetime]
    ) -> User:
        user.failed_login_attempts = failed_attempts
        user.locked_until = locked_until
        await self.db.commit()
        await self.db.refresh(user)
        return user
