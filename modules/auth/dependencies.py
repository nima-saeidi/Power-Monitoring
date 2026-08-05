from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt # (pip install PyJWT) در صورت استفاده از jose از آن ایمپورت کنید

from core.database import get_db
from modules.auth.repository import UserRepository
from modules.auth.models import RoleEnum # مطمئن شوید RoleEnum در models شما وجود دارد

# مسیری که Swagger برای گرفتن توکن به آن ریکوئست می‌زند (با روتر لاگین شما باید یکی باشد)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ⚠️ در محیط عملیاتی این مقادیر باید در فایل env. و pydantic_settings قرار گیرند
SECRET_KEY = "super-secret-key-for-jwt"  
ALGORITHM = "HS256"

# 1. گرفتن کاربر فعلی از روی توکن
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="امکان اعتبارسنجی توکن وجود ندارد.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # دیکد کردن توکن
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # فرض می‌کنیم نام کاربری یا ایمیل را در فیلد sub ذخیره کرده‌اید
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError: # اگر از python-jose استفاده می‌کنید این را به JWTError تغییر دهید
        raise credentials_exception

    # پیدا کردن کاربر از دیتابیس
    repo = UserRepository(db)
    # متد زیر را اگر نام دیگری در ریپازیتوری دارد اصلاح کنید (مثلا get_user_by_email)
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

# require_admin = RoleChecker([Role.ADMIN])

# # اپراتورها و کارشناسان فنی مجازند
# require_operator_or_tech = RoleChecker([Role.ADMIN, Role.OPERATOR, Role.TECH_EXPERT])

# require_any_auth = RoleChecker([Role.ADMIN, Role.OPERATOR, Role.TECH_EXPERT, Role.VIEWER])
