import random
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from main_api.core.config import settings
from main_api.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from main_api.core.email import send_reset_code_email
from main_api.modules.auth.repository import UserRepository
from main_api.modules.auth.schemas import (
    AdminRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    UserProfileUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyCodeRequest
)
from main_api.modules.settings.service import SettingService

# فرض بر این است که RabbitMQPublisher را ایمپورت کرده‌اید
from main_api.core.rabbitmq import RabbitMQPublisher


class AuthService:
    # تزریق وابستگی Publisher به کلاس اضافه شد
    def __init__(self, repository: UserRepository, publisher: RabbitMQPublisher):
        self.repo = repository
        self.publisher = publisher

        # نام روتینگ کی برای صف‌های دیتابیس رابطه‌ای (کاربران)
        self.db_routing_key = "db.users.write"

    # ==========================================
    # متدهای نوشتنی (Event-Driven)
    # ==========================================

    async def register_admin(self, data: AdminRegisterRequest):
        existing_user = await self.repo.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این ایمیل قبلاً در سامانه ثبت شده است."
            )

        if data.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="این شماره تلفن قبلاً ثبت شده است."
                )

        hashed_pwd = hash_password(data.password)

        # ساخت پیلود برای RabbitMQ
        event_payload = {
            "action": "CREATE_USER",
            "data": {
                "name": data.name,
                "email": data.email,
                "phone_number": data.phone_number,
                "hashed_password": hashed_pwd,
                "role": "admin",
                "is_active": True
            }
        }
        await self.publisher.publish_event(self.db_routing_key, event_payload)

        # برگرداندن وضعیت Accepted (چون هنوز آیدی کاربر در دیتابیس ساخته نشده است)
        return {"status": "accepted", "message": "درخواست ثبت ادمین در صف پردازش قرار گرفت."}

    async def create_user(self, data: UserCreate):
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="این ایمیل قبلاً ثبت شده است.")

        if data.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت شده است.")

        hashed_pwd = hash_password(data.password)

        event_payload = {
            "action": "CREATE_USER",
            "data": {
                "name": data.name,
                "email": data.email,
                "phone_number": data.phone_number,
                "hashed_password": hashed_pwd,
                "role": data.role,
                "is_active": data.is_active
            }
        }
        await self.publisher.publish_event(self.db_routing_key, event_payload)
        return {"status": "accepted", "message": "درخواست ایجاد کاربر در صف پردازش قرار گرفت."}

    async def update_user(self, user_id: int, data: UserUpdate):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if data.email and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise HTTPException(status_code=400, detail="این ایمیل توسط شخص دیگری ثبت شده است.")

        if data.phone_number and data.phone_number != user.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن توسط شخص دیگری ثبت شده است.")

        update_data = {}
        if data.name: update_data["name"] = data.name
        if data.email: update_data["email"] = data.email
        if data.phone_number: update_data["phone_number"] = data.phone_number
        if data.role: update_data["role"] = data.role
        if data.is_active is not None: update_data["is_active"] = data.is_active
        if data.password: update_data["hashed_password"] = hash_password(data.password)

        if update_data:
            event_payload = {
                "action": "UPDATE_USER",
                "user_id": user_id,
                "data": update_data
            }
            await self.publisher.publish_event(self.db_routing_key, event_payload)

        return {"status": "accepted", "message": "درخواست بروزرسانی کاربر در صف قرار گرفت."}

    async def update_profile(self, user_id: int, data: UserProfileUpdate):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if data.phone_number and data.phone_number != user.phone_number:
            existing_phone = await self.repo.get_by_phone_number(data.phone_number)
            if existing_phone:
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً در سیستم ثبت شده است.")

        update_data = {}
        if data.name is not None: update_data["name"] = data.name
        if data.phone_number is not None: update_data["phone_number"] = data.phone_number

        if update_data:
            event_payload = {
                "action": "UPDATE_USER",
                "user_id": user_id,
                "data": update_data
            }
            await self.publisher.publish_event(self.db_routing_key, event_payload)

        return {"status": "accepted", "message": "درخواست بروزرسانی پروفایل در صف قرار گرفت."}

    async def change_password(self, user_id: int, data: ChangePasswordRequest):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if not verify_password(data.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز عبور فعلی اشتباه است.")

        if verify_password(data.new_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="رمز عبور جدید نمی‌تواند با رمز عبور فعلی یکسان باشد.")

        event_payload = {
            "action": "UPDATE_USER",
            "user_id": user_id,
            "data": {"hashed_password": hash_password(data.new_password)}
        }
        await self.publisher.publish_event(self.db_routing_key, event_payload)

        return {"status": "accepted", "message": "درخواست تغییر رمز عبور در صف قرار گرفت."}

    async def reset_password(self, data: ResetPasswordRequest):
        try:
            payload = jwt.decode(
                data.reset_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            token_type: str = payload.get("type")

            if not email or token_type != "password_reset":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توکن نامعتبر است.")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="توکن بازنشانی رمز عبور منقضی شده یا نامعتبر است.")

        user = await self.repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربر یافت نشد.")

        event_payload = {
            "action": "UPDATE_USER",
            "user_id": user.id,
            "data": {"hashed_password": hash_password(data.new_password)}
        }
        await self.publisher.publish_event(self.db_routing_key, event_payload)

        return {"status": "accepted", "message": "درخواست بازنشانی رمز عبور در صف قرار گرفت."}

    async def delete_user(self, user_id: int):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        event_payload = {
            "action": "DELETE_USER",
            "user_id": user_id
        }
        await self.publisher.publish_event(self.db_routing_key, event_payload)

        return {"status": "accepted", "message": "درخواست حذف کاربر در صف قرار گرفت."}

    # ==========================================
    # متدهای خواندنی (بدون تغییر در منطق)
    # ==========================================

    async def login(self, data: LoginRequest, db: AsyncSession) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربری با این ایمیل یافت نشد.")

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز عبور اشتباه است.")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="حساب کاربری غیرفعال است.")

        db_settings = await SettingService.get_or_create_settings(db)

        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires_delta = timedelta(minutes=db_settings.access_token_expire_minutes)
        expire_time = now + expires_delta

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=expires_delta
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            expires_at=expire_time,
            user=UserResponse.model_validate(user)
        )

    async def get_all_users(self) -> list[UserResponse]:
        users = await self.repo.get_all()
        return [UserResponse.model_validate(u) for u in users]

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        return UserResponse.model_validate(user)

    async def forgot_password(self, data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
        user = await self.repo.get_by_email(data.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربری با این ایمیل یافت نشد.")

        code = str(random.randint(100000, 999999))
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        session_token = jwt.encode(
            {"sub": user.email, "code": code, "type": "otp_session", "exp": expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        background_tasks.add_task(send_reset_code_email, user.email, code)

        return {"message": "کد تأیید به ایمیل شما ارسال شد.", "session_token": session_token}

    async def verify_reset_code(self, data: VerifyCodeRequest):
        try:
            payload = jwt.decode(
                data.session_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            expected_code: str = payload.get("code")
            token_type: str = payload.get("type")

            if not email or not expected_code or token_type != "otp_session":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توکن جلسه نامعتبر است.")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن جلسه منقضی شده یا نامعتبر است.")

        if str(data.code).strip() != str(expected_code).strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تایید وارد شده اشتباه است.")

        reset_expire = datetime.now(timezone.utc) + timedelta(minutes=10)
        reset_token = jwt.encode(
            {"sub": email, "type": "password_reset", "exp": reset_expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        return {"message": "کد تایید شد.", "reset_token": reset_token}
