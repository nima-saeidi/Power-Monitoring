from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# ایمپورت تنظیمات از خود سرویس تله‌متری
from core.config import settings

# ساخت موتور دیتابیس غیرهمگام
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # تنظیمات بهینه برای Connection Pool در سرویس تله‌متری که دائم در حال نوشتن است
    pool_size=10,
    max_overflow=20
)

# ساخت Session Maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency برای استفاده در روت‌های FastAPI تله‌متری (اگر روت داشته باشید)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
