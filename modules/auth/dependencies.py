from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError

from core.database import get_db
from core.config import settings
from modules.auth.repository import UserRepository
from modules.auth.models import RoleEnum

# مسیری که Swagger برای گرفتن توکن به آن ریکوئست می‌زند
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 1. گرفتن کاربر فعلی از روی توکن (چک کردن صحت توکن)
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="امکان اعتبارسنجی توکن وجود ندارد.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # دقت کنید که ما ایمیل را در توکن ذخیره کرده بودیم
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


# 2. کلاس بررسی نقش‌ها (داینامیک)
class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    # وقتی این کلاس به عنوان Depends صدا زده می‌شود، اول get_current_user (و توکن) چک می‌شود
    def __call__(self, current_user = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="شما مجوز لازم برای انجام این عملیات را ندارید."
            )
        return current_user


# ==========================================
# 3. ساختن متغیرهای آماده برای استفاده در router.py
# ==========================================

# چک کردن فقط ادمین
require_admin = RoleChecker([RoleEnum.ADMIN])

# چک کردن فقط اپراتور فنی
require_operator = RoleChecker([RoleEnum.TECHNICAL_OPERATOR])

# چک کردن ادمین یا اپراتور فنی
require_tech_or_admin = RoleChecker([RoleEnum.ADMIN, RoleEnum.TECHNICAL_OPERATOR])
