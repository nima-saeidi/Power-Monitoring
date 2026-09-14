from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from main_api.modules.auth.models import User

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
