from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from main_api.core.database import get_db
from main_api.core.config import settings
from main_api.modules.auth.repository import UserRepository
from main_api.modules.auth.models import RoleEnum

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
        if email is None:
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
        
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="شما مجوز لازم برای انجام این عملیات را ندارید."
            )
        return current_user


require_admin = RoleChecker([RoleEnum.ADMIN])
require_operator = RoleChecker([RoleEnum.TECHNICAL_OPERATOR])
require_tech_or_admin = RoleChecker([RoleEnum.ADMIN, RoleEnum.TECHNICAL_OPERATOR])
