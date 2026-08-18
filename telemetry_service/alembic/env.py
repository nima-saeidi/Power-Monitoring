import sys
import os
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# اضافه کردن مسیر فعلی به sys.path تا پایتون ماژول‌ها را پیدا کند
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# یا اگر env.py داخل پوشه alembic است، از این استفاده کنید:
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# حذف پیشوند telemetry_service و ایمپورت مستقیم از core
from core.database import Base
target_metadata = Base.metadata

# این تنظیمات فایل alembic.ini است
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# 2. تابع اجرای مایگریشن که توسط run_sync صدا زده می‌شود
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

# 3. تابع Async برای اتصال به دیتابیس
async def run_async_migrations() -> None:
    # ساخت کانکشن ناهمگام
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # اجرای تابع do_run_migrations به صورت همگام درون بستر ناهمگام
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # 4. اجرای تابع ناهمگام با asyncio
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
