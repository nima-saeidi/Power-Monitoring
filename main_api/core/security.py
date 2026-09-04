from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from main_api.core.config import settings


def hash_password(password: str) -> str:
    """هش کردن پسورد خام با استفاده از bcrypt"""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """اعتبارسنجی پسورد ورودی با پسورد هش‌شده"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_token(data: dict, expires_delta: timedelta) -> str:
    """تولید جنریک انواع توکن JWT"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """تولید Access Token برای ورود به سیستم"""
    delta = expires_delta or timedelta(minutes=15)
    return create_token(data, delta)


def decode_token(token: str) -> dict:
    """
    دیکود و اعتبارسنجی توکن
    در صورت منقضی بودن یا نامعتبر بودن، PyJWTError برمی‌گرداند
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
