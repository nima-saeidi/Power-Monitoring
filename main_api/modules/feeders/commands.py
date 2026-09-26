"""
فرمان قطع/وصل فیدر با تأیید دومرحله‌ای ایمیلی (به‌جای پیامک):

۱. request: کاربر (ادمین/اپراتور فنی) فرمان را درخواست می‌کند؛ کد ۶ رقمی به ایمیل خودش ارسال
   و یک challenge_token (JWT کوتاه‌عمر که فقط هش کد را دارد) برگردانده می‌شود.
۲. confirm: با کد و challenge_token، فرمان به دستگاه ارسال می‌شود.

توکن یک‌بار مصرف است، فقط برای همان کاربر/فیدر/فرمان معتبر است و بعد از ۵ کد اشتباه باطل می‌شود.
Coil با مقدار True یعنی «وصل» و False یعنی «قطع»؛ اگر دستگاهی برعکس باشد،
metadata_info فیدر: {"command_inverted": true}
"""
import asyncio
import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError

from main_api.core.broker import send_notification_to_queue
from main_api.core.config import settings
from main_api.core.email_templates import build_command_code_email_html
from main_api.modules.audit_logs.services import send_audit_log
from main_api.modules.feeders.schemas import CommandConfirmRequest

CODE_TTL_SECONDS = 90
MAX_CODE_ATTEMPTS = 5
ACTION_LABELS = {"connect": "وصل", "disconnect": "قطع"}

# وضعیت توکن‌های فعال (فقط در حافظه‌ی همین پروسه؛ main_api با یک worker اجرا می‌شود):
# jti -> زمان انقضا (برای توکن مصرف‌شده) / تعداد تلاش ناموفق
_used_challenges: Dict[str, float] = {}
_failed_attempts: Dict[str, int] = {}


def _code_digest(jti: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"cmd:{jti}:{code}".encode(), hashlib.sha256).hexdigest()


def _prune() -> None:
    now = time.time()
    for jti in [j for j, exp in _used_challenges.items() if exp < now]:
        _used_challenges.pop(jti, None)
        _failed_attempts.pop(jti, None)


def _resolve_target(feeder) -> dict:
    ip = feeder.ip_address or (feeder.post.ip_address if feeder.post else None)
    if feeder.control_register is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="برای این فیدر آدرس رجیستر فرمان (control_register) تعریف نشده است.")
    if not ip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="برای این فیدر و پست آن آدرس IP تعریف نشده است.")
    return {
        "ip_address": ip,
        "port": feeder.port or (feeder.post.port if feeder.post else None) or 502,
        "slave_id": feeder.modbus_address if feeder.modbus_address is not None else 1,
        "register_address": feeder.control_register,
    }


async def request_command(feeder, action: str, user) -> dict:
    _resolve_target(feeder)  # خطای پیکربندی قبل از ارسال کد گزارش شود
    jti = uuid.uuid4().hex
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.now(timezone.utc) + timedelta(seconds=CODE_TTL_SECONDS)
    token = jwt.encode({
        "type": "command_challenge", "sub": str(user.id), "feeder_id": feeder.id,
        "action": action, "jti": jti, "code_hash": _code_digest(jti, code), "exp": expires,
    }, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    action_label = ACTION_LABELS[action]
    await send_notification_to_queue(
        title=f"کد تأیید فرمان {action_label} فیدر {feeder.name}",
        message=(f"کد تأیید فرمان «{action_label}» فیدر «{feeder.name}»: {code}\n"
                 f"این کد {CODE_TTL_SECONDS} ثانیه اعتبار دارد."),
        html_message=build_command_code_email_html(code, feeder.name, action_label, CODE_TTL_SECONDS),
        channel="email",
        email_addresses=[user.email],
        priority="high",
        metadata={"event_type": "command_code", "feeder_id": feeder.id, "user_id": user.id},
    )
    asyncio.create_task(send_audit_log(
        action="FEEDER_COMMAND_REQUESTED", user_id=user.id, username=user.email, user_role=user.role,
        success=True, severity="WARNING", feeder_id=feeder.id,
        description=f"درخواست فرمان «{action_label}» برای فیدر «{feeder.name}»؛ کد تأیید ایمیل شد.",
    ))
    return {"message": "کد تأیید به ایمیل شما ارسال شد.", "challenge_token": token, "expires_in": CODE_TTL_SECONDS}


async def confirm_command(feeder, data: CommandConfirmRequest, user) -> dict:
    # ایمپورت محلی: telemetry.service خودش ماژول‌های زیادی را بارگذاری می‌کند
    from main_api.modules.telemetry.service import TelemetryService

    _prune()
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن فرمان منقضی شده یا نامعتبر است.")
    try:
        payload = jwt.decode(data.challenge_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except PyJWTError:
        raise invalid
    jti = payload.get("jti", "")
    if (payload.get("type") != "command_challenge" or payload.get("sub") != str(user.id)
            or payload.get("feeder_id") != feeder.id or jti in _used_challenges):
        raise invalid

    if not hmac.compare_digest(_code_digest(jti, data.code.strip()), payload.get("code_hash", "")):
        _failed_attempts[jti] = _failed_attempts.get(jti, 0) + 1
        if _failed_attempts[jti] >= MAX_CODE_ATTEMPTS:
            _used_challenges[jti] = payload["exp"]
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="تعداد تلاش‌های ناموفق زیاد بود؛ دوباره درخواست فرمان دهید.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تأیید اشتباه است.")
    _used_challenges[jti] = payload["exp"]

    action = payload["action"]
    action_label = ACTION_LABELS[action]
    target = _resolve_target(feeder)
    inverted = bool((feeder.metadata_info or {}).get("command_inverted"))
    value = (action == "connect") != inverted
    try:
        result = await TelemetryService.send_coil_command(value=value, **target)
    except HTTPException as e:
        asyncio.create_task(send_audit_log(
            action="FEEDER_COMMAND_FAILED", user_id=user.id, username=user.email, user_role=user.role,
            success=False, severity="CRITICAL", feeder_id=feeder.id,
            description=f"اجرای فرمان «{action_label}» فیدر «{feeder.name}» ناموفق بود: {e.detail}",
        ))
        raise
    asyncio.create_task(send_audit_log(
        action="FEEDER_COMMAND_EXECUTED", user_id=user.id, username=user.email, user_role=user.role,
        success=True, severity="CRITICAL", feeder_id=feeder.id,
        description=f"فرمان «{action_label}» فیدر «{feeder.name}» اجرا شد.",
    ))
    return {"message": f"فرمان «{action_label}» با موفقیت اجرا شد.", "action": action, "device": result}
