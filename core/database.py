from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings  # فرض بر این است که فایل کانفیگ در این مسیر قرار دارد

# آدرس دیتابیس SQLite محلی (فایل app.db در مسیر اصلی پروژه ساخته می‌شود)

engine = create_async_engine(
    settings.DATABASE_URL,  # استفاده از آدرس پستگرس
    echo=False, 
    # connect_args={"check_same_thread": False} -> این خط مخصوص SQLite است و برای Postgres باید حذف شود
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
