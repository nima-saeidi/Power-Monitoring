import random
import uuid
import asyncio
from math import ceil
from typing import Optional
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
from main_api.modules.users.repository import UserRepository
from main_api.modules.users.schemas import UserResponse
from main_api.modules.auth.schemas import (
    AdminRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfileUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyCodeRequest
)
from main_api.modules.settings.service import SettingService
from main_api.core.broker import RabbitMQPublisher, send_notification_to_queue
from main_api.core.email_templates import build_reset_code_email_html

# ایمپورت تابع ارسال لاگ
from main_api.modules.audit_logs.services import send_audit_log, schedule_audit_log


class AuthService:
    """احراز هویت: لاگین، پروفایل شخصی، تغییر/بازیابی رمز عبور و ثبت‌نام ادمین اولیه.
    برای مدیریت کاربران توسط ادمین (CRUD) به main_api.modules.users.service.UserService مراجعه کنید."""

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

    async def login(self, data: LoginRequest, background_tasks: Optional[BackgroundTasks] = None) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user:
            # ارسال لاگ خطا قبل از توقف ریکوئست
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", username=data.email, success=False,
                severity="WARNING", description="کاربری با این ایمیل یافت نشد."
            ))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربری با این ایمیل یافت نشد.")

        # تنظیمات سیستم یک‌بار در ابتدا خوانده می‌شود تا هم در بررسی قفل حساب و
        # هم در محاسبه‌ی مدت اعتبار توکن از همان مقادیر به‌روز استفاده شود.
        db_settings = await SettingService.get_or_create_settings(self.db)

        self._ensure_account_not_locked(user)

        if not verify_password(data.password, user.hashed_password):
            await self._register_failed_login(user, db_settings)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز عبور اشتباه است.")

        if not user.is_active:
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING", description="حساب کاربری غیرفعال است."
            ))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="حساب کاربری غیرفعال است.")

        # ورود موفق: هر شمارنده‌ی تلاش ناموفق قبلی پاک می‌شود
        await self._reset_login_attempts(user)

        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires_delta = timedelta(minutes=db_settings.access_token_expire_minutes)
        expire_time = now + expires_delta

        # اصلاح ساختار توکن که به هم ریخته بود
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=expires_delta
        )

        # ارسال لاگ موفقیت آمیز در پس‌زمینه
        schedule_audit_log(
            background_tasks,
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

    # ==========================================
    # قفل حساب بر اساس max_login_attempts / lockout_duration_minutes
    # (تنظیمات سیستم -> main_api/modules/settings)
    # ==========================================

    def _ensure_account_not_locked(self, user) -> None:
        """اگر حساب هنوز طبق lockout_duration_minutes قفل است، درخواست را متوقف می‌کند."""
        if not user.locked_until:
            return

        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)

        if locked_until > now:
            remaining_minutes = max(1, ceil((locked_until - now).total_seconds() / 60))
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_BLOCKED_LOCKED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING",
                description=f"تلاش برای ورود به حساب قفل‌شده. {remaining_minutes} دقیقه تا باز شدن قفل باقی مانده."
            ))
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"حساب کاربری به دلیل تلاش‌های ناموفق مکرر قفل شده است. لطفاً {remaining_minutes} دقیقه دیگر تلاش کنید."
            )

    async def _register_failed_login(self, user, db_settings) -> None:
        """افزایش شمارنده‌ی تلاش ناموفق و قفل کردن حساب در صورت رسیدن به max_login_attempts."""
        new_attempts = (user.failed_login_attempts or 0) + 1
        should_lock = new_attempts >= db_settings.max_login_attempts

        locked_until = (
            datetime.now(timezone.utc) + timedelta(minutes=db_settings.lockout_duration_minutes)
            if should_lock else None
        )
        await self.repo.update_login_state(
            user,
            failed_attempts=0 if should_lock else new_attempts,
            locked_until=locked_until,
        )

        if should_lock:
            asyncio.create_task(send_audit_log(
                action="USER_ACCOUNT_LOCKED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="CRITICAL",
                description=(
                    f"حساب پس از {db_settings.max_login_attempts} تلاش ناموفق متوالی "
                    f"به مدت {db_settings.lockout_duration_minutes} دقیقه قفل شد."
                )
            ))
        else:
            asyncio.create_task(send_audit_log(
                action="USER_LOGIN_FAILED", user_id=user.id, username=user.email, user_role=user.role,
                success=False, severity="WARNING",
                description=f"رمز عبور اشتباه است. تلاش {new_attempts} از {db_settings.max_login_attempts}."
            ))

    async def _reset_login_attempts(self, user) -> None:
        """پس از ورود موفق، شمارنده‌ی تلاش ناموفق و قفل احتمالی حساب را پاک می‌کند."""
        if user.failed_login_attempts or user.locked_until:
            await self.repo.update_login_state(user, failed_attempts=0, locked_until=None)

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

        # ارسال ایمیل دیگر در main_api انجام نمی‌شود؛ فقط رویداد به صف notification_events
        # منتشر می‌شود تا notification_service آن را از طریق EmailProvider ارسال کند.
        background_tasks.add_task(
            send_notification_to_queue,
            title="کد تأیید بازیابی رمز عبور",
            message=(
                f"کد تأیید بازیابی رمز عبور شما: {code}\n"
                "این کد به مدت ۵ دقیقه معتبر است. اگر این درخواست را نداده‌اید، این پیام را نادیده بگیرید."
            ),
            html_message=build_reset_code_email_html(code),
            channel="email",
            email_addresses=[user.email],
            priority="high",
            metadata={"event_type": "password_reset_otp", "user_id": user.id},
        )

        background_tasks.add_task(
            send_audit_log, action="PASSWORD_RESET_REQUESTED", user_id=user.id,
            username=user.email, user_role=user.role, success=True, severity="INFO"
        )

        return {"message": "کد تأیید به ایمیل شما ارسال شد.", "session_token": token}

    async def verify_reset_code(self, data: VerifyCodeRequest, background_tasks: Optional[BackgroundTasks] = None):
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

        schedule_audit_log(
            background_tasks, action="PASSWORD_RESET_VERIFIED", username=email, success=True, severity="INFO"
        )

        return {"message": "کد تایید شد.", "reset_token": reset_token}

    # ==========================================
    # متدهای نوشتنی (Event-Driven)
    # ==========================================

    async def register_admin(self, data: AdminRegisterRequest, background_tasks: Optional[BackgroundTasks] = None):
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
                "hashed_password": hash_password(data.password),
                "role": "admin",
                "is_active": True
            }
        })

        schedule_audit_log(
            background_tasks, action="REGISTER_ADMIN_QUEUED", username=data.email,
            success=True, severity="INFO", description="درخواست ثبت ادمین در صف قرار گرفت"
        )
        return {"status": "accepted", "message": "درخواست ثبت ادمین در صف پردازش قرار گرفت."}

    async def update_profile(self, user_id: int, data: UserProfileUpdate, background_tasks: Optional[BackgroundTasks] = None):
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

            schedule_audit_log(
                background_tasks, action="UPDATE_PROFILE_QUEUED", user_id=user.id, username=user.email,
                user_role=user.role, success=True, severity="INFO"
            )
        return {"status": "accepted", "message": "درخواست بروزرسانی پروفایل در صف قرار گرفت."}

    async def change_password(self, user_id: int, data: ChangePasswordRequest, background_tasks: Optional[BackgroundTasks] = None):
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
            "data": {"hashed_password": hash_password(data.new_password)}
        })

        schedule_audit_log(
            background_tasks, action="CHANGE_PASSWORD_QUEUED", user_id=user.id, username=user.email,
            user_role=user.role, success=True, severity="INFO"
        )
        return {"status": "accepted", "message": "درخواست تغییر رمز عبور در صف قرار گرفت."}

    async def reset_password(self, data: ResetPasswordRequest, background_tasks: Optional[BackgroundTasks] = None):
        try:
            payload = jwt.decode(data.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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
            "data": {"hashed_password": hash_password(data.new_password)}
        })

        schedule_audit_log(
            background_tasks, action="RESET_PASSWORD_QUEUED", user_id=user.id, username=user.email,
            user_role=user.role, success=True, severity="INFO"
        )
        return {"status": "accepted", "message": "درخواست بازنشانی رمز عبور در صف قرار گرفت."}
