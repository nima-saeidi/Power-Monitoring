from main_api.core.tasks import fire_and_forget
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from main_api.core.broker import send_notification_to_queue
from main_api.core.config import settings
from main_api.core.email_templates import build_command_code_email_html
from main_api.modules.audit_logs.services import send_audit_log
from main_api.modules.feeders.models import CommandChallenge
from main_api.modules.feeders.schemas import CommandConfirmRequest

CODE_TTL_SECONDS = 90
MAX_CODE_ATTEMPTS = 5
ACTION_LABELS = {"connect": "وصل", "disconnect": "قطع"}


def _code_digest(jti: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"cmd:{jti}:{code}".encode(), hashlib.sha256).hexdigest()


async def _prune(db: AsyncSession) -> None:
    await db.execute(delete(CommandChallenge).where(CommandChallenge.expires_at < datetime.now(timezone.utc)))
    await db.commit()


async def _record_failure(db: AsyncSession, jti: str, expires_at: datetime) -> int:
    attempts = CommandChallenge.failed_attempts + 1
    stmt = (
        pg_insert(CommandChallenge)
        .values(jti=jti, failed_attempts=1, consumed=False, expires_at=expires_at)
        .on_conflict_do_update(
            index_elements=[CommandChallenge.jti],
            set_={"failed_attempts": attempts, "consumed": attempts >= MAX_CODE_ATTEMPTS},
        )
        .returning(CommandChallenge.failed_attempts)
    )
    result = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return result


async def _consume(db: AsyncSession, jti: str, expires_at: datetime) -> bool:
    """Atomically mark a challenge as used; False if it was already used."""
    stmt = (
        pg_insert(CommandChallenge)
        .values(jti=jti, consumed=True, expires_at=expires_at)
        .on_conflict_do_update(
            index_elements=[CommandChallenge.jti],
            set_={"consumed": True},
            where=CommandChallenge.consumed.is_(False),
        )
        .returning(CommandChallenge.jti)
    )
    consumed = (await db.execute(stmt)).scalar_one_or_none() is not None
    await db.commit()
    return consumed


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
    _resolve_target(feeder)
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
    fire_and_forget(send_audit_log(
        action="FEEDER_COMMAND_REQUESTED", user_id=user.id, username=user.email, user_role=user.role,
        success=True, severity="WARNING", feeder_id=feeder.id,
        description=f"درخواست فرمان «{action_label}» برای فیدر «{feeder.name}»؛ کد تأیید ایمیل شد.",
    ))
    return {"message": "کد تأیید به ایمیل شما ارسال شد.", "challenge_token": token, "expires_in": CODE_TTL_SECONDS}


async def confirm_command(db: AsyncSession, feeder, data: CommandConfirmRequest, user) -> dict:
    from main_api.modules.telemetry.service import TelemetryService

    await _prune(db)
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن فرمان منقضی شده یا نامعتبر است.")
    try:
        payload = jwt.decode(data.challenge_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except PyJWTError:
        raise invalid
    jti = payload.get("jti", "")
    if (payload.get("type") != "command_challenge" or payload.get("sub") != str(user.id)
            or payload.get("feeder_id") != feeder.id or not jti):
        raise invalid
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    state = await db.get(CommandChallenge, jti)
    if state is not None and state.consumed:
        raise invalid

    if not hmac.compare_digest(_code_digest(jti, data.code.strip()), payload.get("code_hash", "")):
        if await _record_failure(db, jti, expires_at) >= MAX_CODE_ATTEMPTS:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="تعداد تلاش‌های ناموفق زیاد بود؛ دوباره درخواست فرمان دهید.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کد تأیید اشتباه است.")
    if not await _consume(db, jti, expires_at):
        raise invalid

    action = payload["action"]
    action_label = ACTION_LABELS[action]
    target = _resolve_target(feeder)
    inverted = bool((feeder.metadata_info or {}).get("command_inverted"))
    value = (action == "connect") != inverted
    try:
        result = await TelemetryService.send_coil_command(value=value, **target)
    except HTTPException as e:
        fire_and_forget(send_audit_log(
            action="FEEDER_COMMAND_FAILED", user_id=user.id, username=user.email, user_role=user.role,
            success=False, severity="CRITICAL", feeder_id=feeder.id,
            description=f"اجرای فرمان «{action_label}» فیدر «{feeder.name}» ناموفق بود: {e.detail}",
        ))
        raise
    fire_and_forget(send_audit_log(
        action="FEEDER_COMMAND_EXECUTED", user_id=user.id, username=user.email, user_role=user.role,
        success=True, severity="CRITICAL", feeder_id=feeder.id,
        description=f"فرمان «{action_label}» فیدر «{feeder.name}» اجرا شد.",
    ))
    return {"message": f"فرمان «{action_label}» با موفقیت اجرا شد.", "action": action, "device": result}
