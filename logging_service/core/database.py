# logging_service/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings

# ساخت موتور Async برای ارتباط با Postgres
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# ساخت Session برای تراکنش‌های دیتابیس
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
