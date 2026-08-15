from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from core.config import settings
import bcrypt

# پیکربندی Passlib برای استفاده از الگوریتم bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # تولید نمک (salt) و هش کردن پسورد
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    # تبدیل بایت به رشته برای ذخیره در دیتابیس
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # بررسی تطابق پسورد وارد شده با هش دیتابیس
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """ایجاد توکن JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # استفاده از زمان پیش‌فرض تعیین شده در تنظیمات
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    
    # ساخت توکن با کلید و الگوریتم موجود در settings
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt
