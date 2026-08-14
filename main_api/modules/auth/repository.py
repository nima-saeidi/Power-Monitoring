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

    # تغییر نام متد و فیلد جستجو به phone_number
    async def get_by_phone_number(self, phone_number: str):
        result = await self.db.execute(select(User).where(User.phone_number == phone_number))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int):
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all(self):
        result = await self.db.execute(select(User))
        return result.scalars().all()

    # جایگزینی national_id با phone_number در ورودی‌ها و ساخت آبجکت
    async def create_user(self, name, email, hashed_password, role, phone_number=None, is_active=True):
        new_user = User(
            name=name,
            email=email,
            phone_number=phone_number,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def delete_user(self, user: User):
        await self.db.delete(user)
        await self.db.commit()

    async def save_changes(self):
        await self.db.commit()
