import hmac
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from main_api.core.database import get_db, AsyncSessionLocal
from main_api.core.config import settings
from main_api.modules.users.repository import UserRepository
from main_api.modules.users.models import RoleEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="امکان اعتبارسنجی توکن وجود ندارد.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        if email is None or payload.get("type", "access") != "access":
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن شما منقضی شده است. لطفاً مجدداً وارد شوید.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_email(email)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="حساب کاربری غیرفعال است.")

    return user


async def authenticate_websocket(token: str | None):
    if not token:
        return None
    try:
        async with AsyncSessionLocal() as db:
            return await get_current_user(token, db)
    except HTTPException:
        return None


async def verify_internal_api_key(x_internal_api_key: str | None = Header(default=None)):
    expected = settings.INTERNAL_API_KEY
    if not expected or not x_internal_api_key or not hmac.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی به این اندپوینت داخلی مجاز نیست.")


def require_page(page: str):
    async def checker(current_user=Depends(get_current_user)):
        if current_user.role == RoleEnum.ADMIN:
            return current_user
        allowed = current_user.allowed_pages
        if allowed is not None and page not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="دسترسی به این بخش برای حساب شما فعال نشده است.")
        return current_user
    return checker


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user=Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="شما مجوز لازم برای انجام این عملیات را ندارید."
            )
        return current_user


require_admin = RoleChecker([RoleEnum.ADMIN])

require_tech_or_admin = RoleChecker([RoleEnum.ADMIN, RoleEnum.TECHNICAL_OPERATOR])

require_any_user = RoleChecker([RoleEnum.ADMIN, RoleEnum.TECHNICAL_OPERATOR, RoleEnum.USER])

require_operator = RoleChecker([RoleEnum.TECHNICAL_OPERATOR])
