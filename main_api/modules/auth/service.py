from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.modules.auth.repository import UserRepository
from main_api.modules.auth.schemas import AdminRegisterRequest, LoginRequest, TokenResponse, UserResponse, UserCreate, \
    UserUpdate, UserProfileUpdate
from main_api.core.security import hash_password, verify_password, create_access_token
from main_api.modules.settings.service import SettingService


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repo = repository

    async def register_admin(self, data: AdminRegisterRequest) -> UserResponse:
        existing_user = await self.repo.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این ایمیل قبلاً در سامانه ثبت شده است."
            )

        if data.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت شده است.")

        hashed_pwd = hash_password(data.password)
        new_user = await self.repo.create_user(
            name=data.name,
            email=data.email,
            phone_number=data.phone_number,
            hashed_password=hashed_pwd,
            role="admin"
        )
        return UserResponse.model_validate(new_user)

    async def login(self, data: LoginRequest, db: AsyncSession) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ایمیل یا رمز عبور اشتباه است."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="حساب کاربری غیرفعال است."
            )

        settings = await SettingService.get_or_create_settings(db)
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=expires_delta
        )

        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user)
        )

    async def create_user(self, data: UserCreate) -> UserResponse:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="این ایمیل قبلاً ثبت شده است.")

        if data.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت شده است.")

        hashed_pwd = hash_password(data.password)
        new_user = await self.repo.create_user(
            name=data.name,
            email=data.email,
            phone_number=data.phone_number,
            hashed_password=hashed_pwd,
            role=data.role,
            is_active=data.is_active
        )
        return UserResponse.model_validate(new_user)

    async def get_all_users(self) -> list[UserResponse]:
        users = await self.repo.get_all()
        return [UserResponse.model_validate(u) for u in users]

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        return UserResponse.model_validate(user)

    async def update_user(self, user_id: int, data: UserUpdate) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if data.email and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise HTTPException(status_code=400, detail="این ایمیل توسط شخص دیگری ثبت شده است.")
            user.email = data.email

        if data.phone_number and data.phone_number != user.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن توسط شخص دیگری ثبت شده است.")
            user.phone_number = data.phone_number

        if data.name: user.name = data.name
        if data.role: user.role = data.role
        if data.is_active is not None: user.is_active = data.is_active
        if data.password: user.hashed_password = hash_password(data.password)

        await self.repo.save_changes()
        return UserResponse.model_validate(user)

    async def update_profile(self, user_id: int, data: UserProfileUpdate) -> UserResponse:
        user = await self.repo.get_by_id(user_id)

        if data.phone_number and data.phone_number != user.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً در سیستم ثبت شده است.")
            user.phone_number = data.phone_number

        if data.name is not None:
            user.name = data.name

        await self.repo.save_changes()
        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: int):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        await self.repo.delete_user(user)
        return {"message": "کاربر با موفقیت حذف شد."}
