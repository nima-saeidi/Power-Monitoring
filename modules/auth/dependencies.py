from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError

from core.database import get_db
from core.config import settings  # 👈 اضافه شدن تنظیمات سراسری
from modules.auth.repository import UserRepository
from modules.auth.models import RoleEnum

# مسیری که Swagger برای گرفتن توکن به آن ریکوئست می‌زند
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 1. گرفتن کاربر فعلی از روی توکن
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="امکان اعتبارسنجی توکن وجود ندارد.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 👈 دیکد کردن توکن با استفاده از تنظیمات env.
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
    except ExpiredSignatureError:
        # 👈 مدیریت دقیق‌تر خطای انقضای توکن
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن شما منقضی شده است. لطفاً مجدداً وارد شوید.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError: 
        raise credentials_exception

    # پیدا کردن کاربر از دیتابیس
    repo = UserRepository(db)
    user = await repo.get_user_by_username(username) 
    
    if user is None:
        raise credentials_exception
        
    return user


# 2. وابستگی (Dependency) مخصوص ادمین
async def get_admin_user(current_user = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="دسترسی غیرمجاز. این عملیات فقط برای ادمین مجاز است."
        )
    return current_user


# 3. وابستگی (Dependency) مخصوص ادمین و اپراتور فنی
async def get_tech_or_admin_user(current_user = Depends(get_current_user)):
    if current_user.role not in [RoleEnum.admin, RoleEnum.technical_operator]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="دسترسی غیرمجاز. فقط ادمین یا اپراتور فنی."
        )
    return current_user


# 4. کلاس بررسی نقش‌ها (بهترین روش برای مدیریت داینامیک دسترسی‌ها)
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

# 💡 نمونه‌های نحوه استفاده در روت‌ها (Router):
# require_admin = RoleChecker([RoleEnum.admin])
# require_operator_or_tech = RoleChecker([RoleEnum.admin, RoleEnum.technical_operator])
