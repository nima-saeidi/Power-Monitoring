import random
import uuid
import asyncio
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
from main_api.core.broker import RabbitMQPublisher

# ایمپورت تابع ارسال لاگ
from main_api.modules.audit_logs.services import send_audit_log


class AuthService:
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

    # ==========================================
    # متدهای خواندنی و لاگین (Direct DB + Cache)
    # ==========================================

    async def login(self, data: LoginRequest, background_tasks: BackgroundTasks) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user:
            # ارسال لاگ خطا قبل از توقف ریکوئست
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", username=data.email, success=False,
                severity="WARNING", description="کاربری با این ایمیل یافت نشد."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربری با این ایمیل یافت نشد.")

        if not verify_password(data.password, user.hashed_password):
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING", description="رمز عبور اشتباه است."
            ))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز عبور اشتباه است.")

        if not user.is_active:
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING", description="حساب کاربری غیرفعال است."
            ))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="حساب کاربری غیرفعال است.")

        db_settings = await SettingService.get_or_create_settings(self.db)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires_delta = timedelta(minutes=db_settings.access_token_expire_minutes)
        expire_time = now + expires_delta

        # اصلاح ساختار توکن که به هم ریخته بود
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=expires_delta
        )

        # ارسال لاگ موفقیت آمیز در پس‌زمینه
        background_tasks.add_task(
            send_audit_log,
            action="USER_LOGIN",
            user_id=user.id,
            username=user.email,
            user_role=user.role,
            success=True,
            severity="INFO",
            description="ورود موفق به سیستم"
        )

        return TokenResponse(
            access_token=access_token,
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
            asyncio.create_task(send_audit_log(
                action="PASSWORD_RESET_REQUEST_FAILED", username=data.email,
                success=False, severity="WARNING", description="درخواست فراموشی رمز برای ایمیل ناموجود"
            ))
            return {"message": "اگر ایمیل در سیستم موجود باشد، کد تأیید ارسال خواهد شد."}

        code = str(random.randint(100000, 999999))
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)

        token = jwt.encode(
            {"sub": user.email, "code": code, "type": "otp_session", "exp": expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        background_tasks.add_task(send_reset_code_email, user.email, code)

        background_tasks.add_task(
            send_audit_log, action="PASSWORD_RESET_REQUESTED", user_id=user.id,
            username=user.email, user_role=user.role, success=True, severity="INFO"
        )

        return {"message": "کد تأیید به ایمیل شما ارسال شد.", "token": token}

    async def verify_reset_code(self, data: VerifyCodeRequest, background_tasks: BackgroundTasks):
        try:
            payload = jwt.decode(
                data.token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            expected_code: str = payload.get("code")
            token_type: str = payload.get("type")

            if not email or not expected_code or token_type != "otp_session":
                asyncio.create_task(send_audit_log(
                    action="PASSWORD_RESET_VERIFY_FAILED", success=False, severity="WARNING",
                    description="توکن جلسه نامعتبر است."
                ))
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توکن جلسه نامعتبر است.")
        except JWTError:
            asyncio.create_task(send_audit_log(
                action="PASSWORD_RESET_VERIFY_FAILED", success=False, severity="WARNING",
                description="توکن جلسه منقضی شده یا نامعتبر است."
            ))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن جلسه منقضی شده یا نامعتبر است.")

        if str(data.code).strip() != str(expected_code).strip():
            asyncio.create_task(send_audit_log(
                action="PASSWORD_RESET_VERIFY_FAILED", username=email, success=False, severity="WARNING",
                description="کد تایید اشتباه است."
            ))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تایید وارد شده اشتباه است.")

        reset_expire = datetime.now(timezone.utc) + timedelta(minutes=10)
        reset_token = jwt.encode(
            {"sub": email, "type": "password_reset", "exp": reset_expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        background_tasks.add_task(
            send_audit_log, action="PASSWORD_RESET_VERIFIED", username=email, success=True, severity="INFO"
        )

        return {"message": "کد تایید شد.", "token": reset_token}

    # ==========================================
    # متدهای نوشتنی (Event-Driven)
    # ==========================================

    async def register_admin(self, data: AdminRegisterRequest, background_tasks: BackgroundTasks):
        if await self.repo.get_by_email(data.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="این ایمیل قبلاً ثبت شده است.")
        if data.phone_number and await self.repo.get_by_phone_number(data.phone_number):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="این شماره تلفن قبلاً ثبت شده است.")

        await self._publish({
            "entity": "user",
            "action": "CREATE_USER",
            "data": {
                "name": data.name,
                "email": data.email,
                "phone_number": data.phone_number,
                "hashed_password": hash_password(data.password),  # اصلاح شد
                "role": "admin",
                "is_active": True
            }
        })

        background_tasks.add_task(
            send_audit_log, action="REGISTER_ADMIN_QUEUED", username=data.email,
            success=True, severity="INFO", description="درخواست ثبت ادمین در صف قرار گرفت"
        )
        return {"status": "accepted", "message": "درخواست ثبت ادمین در صف پردازش قرار گرفت."}

    async def create_user(self, data: UserCreate, background_tasks: BackgroundTasks, current_user: UserResponse = None):
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
                "hashed_password": hash_password(data.password),  # اصلاح شد
                "role": data.role,
                "is_active": data.is_active,
                "sms_notification_enabled": data.sms_notification_enabled
            }
        })

        actor_id = current_user.id if current_user else None
        actor_name = current_user.email if current_user else None

        background_tasks.add_task(
            send_audit_log, action="CREATE_USER_QUEUED", user_id=actor_id, username=actor_name,
            success=True, severity="INFO", description=f"درخواست ایجاد کاربر {data.email} در صف قرار گرفت"
        )
        return {"status": "accepted", "message": "درخواست ایجاد کاربر در صف پردازش قرار گرفت."}

    async def update_user(self, user_id: int, data: UserUpdate, background_tasks: BackgroundTasks,
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

            background_tasks.add_task(
                send_audit_log, action="UPDATE_USER_QUEUED", user_id=actor_id, username=actor_name,
                success=True, severity="INFO", description=f"بروزرسانی اطلاعات کاربر با ID {user_id}"
            )
        return {"status": "accepted", "message": "درخواست بروزرسانی کاربر در صف قرار گرفت."}

    async def update_profile(self, user_id: int, data: UserProfileUpdate, background_tasks: BackgroundTasks):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if data.phone_number and data.phone_number != user.phone_number:
            if await self.repo.get_by_phone_number(data.phone_number):
                raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت شده است.")

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self._publish({
                "entity": "user",
                "action": "UPDATE_USER",
                "user_id": user_id,
                "data": update_data
            })

            background_tasks.add_task(
                send_audit_log, action="UPDATE_PROFILE_QUEUED", user_id=user.id, username=user.email,
                user_role=user.role, success=True, severity="INFO"
            )
        return {"status": "accepted", "message": "درخواست بروزرسانی پروفایل در صف قرار گرفت."}

    async def change_password(self, user_id: int, data: ChangePasswordRequest, background_tasks: BackgroundTasks):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        if not verify_password(data.old_password, user.hashed_password):
            asyncio.create_task(send_audit_log(
                action="CHANGE_PASSWORD_FAILED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING", description="رمز عبور فعلی اشتباه است."
            ))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رمز عبور فعلی اشتباه است.")

        if verify_password(data.new_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="رمز عبور جدید نمی‌تواند با قبلی یکسان باشد.")

        await self._publish({
            "entity": "user",
            "action": "UPDATE_USER",
            "user_id": user_id,
            "data": {"hashed_password": hash_password(data.new_password)}  # اصلاح شد
        })

        background_tasks.add_task(
            send_audit_log, action="CHANGE_PASSWORD_QUEUED", user_id=user.id, username=user.email,
            user_role=user.role, success=True, severity="INFO"
        )
        return {"status": "accepted", "message": "درخواست تغییر رمز عبور در صف قرار گرفت."}

    async def reset_password(self, data: ResetPasswordRequest, background_tasks: BackgroundTasks):
        try:
            payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])  # اصلاح شد
            email: str = payload.get("sub")
            if not email or payload.get("type") != "password_reset":
                raise JWTError
        except JWTError:
            asyncio.create_task(send_audit_log(
                action="RESET_PASSWORD_FAILED", success=False, severity="WARNING",
                description="توکن منقضی شده یا نامعتبر"
            ))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن منقضی شده یا نامعتبر است.")

        user = await self.repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربر یافت نشد.")

        await self._publish({
            "entity": "user",
            "action": "UPDATE_USER",
            "user_id": user.id,
            "data": {"hashed_password": hash_password(data.new_password)}  # اصلاح شد
        })

        background_tasks.add_task(
            send_audit_log, action="RESET_PASSWORD_QUEUED", user_id=user.id, username=user.email,
            user_role=user.role, success=True, severity="INFO"
        )
        return {"status": "accepted", "message": "درخواست بازنشانی رمز عبور در صف قرار گرفت."}

    async def delete_user(self, user_id: int, background_tasks: BackgroundTasks, current_user: UserResponse = None):
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

        background_tasks.add_task(
            send_audit_log, action="DELETE_USER_QUEUED", user_id=actor_id, username=actor_name,
            success=True, severity="CRITICAL", description=f"کاربر با ID {user_id} حذف شد"
        )
        return {"status": "accepted", "message": "درخواست حذف کاربر در صف قرار گرفت."}
