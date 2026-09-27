import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core.config import settings
from core.consumer import start_consumer
from core.errors import install_error_handlers
from modules.routers import router as logs_router

from core.database import engine, Base
import modules.models

logger = logging.getLogger(__name__)


_EXTRA_INDEX_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_action_trgm ON service_logs USING gin (action gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_service_name_trgm ON service_logs USING gin (service_name gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_severity ON service_logs ((details->>'severity'))",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_success ON service_logs ((details->>'success'))",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_service_created ON service_logs (service_name, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_action_created ON service_logs (action, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_service_logs_user_created ON service_logs (user_id, created_at DESC)",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            logger.info("Ensuring reporting indexes exist on service_logs...")
            for statement in _EXTRA_INDEX_STATEMENTS:
                try:
                    await conn.execute(text(statement))
                except Exception as idx_err:
                    logger.warning(f"Could not ensure index ({statement[:60]}...): {idx_err}")

        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    logger.info("Starting RabbitMQ Consumer task...")
    consumer_task = asyncio.create_task(start_consumer())

    yield

    logger.info("Stopping RabbitMQ Consumer task...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("RabbitMQ Consumer task cancelled successfully.")


app = FastAPI(
    title="Power Monitoring - Logging & Audit Service",
    description="Service to consume audit logs from RabbitMQ and store them in PostgreSQL & Graylog",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app, logger)

app.include_router(logs_router, prefix="/api/v1")


@app.get("/", tags=["Health Check"])
async def health_check():
    return {
        "service": "Logging & Audit Service",
        "status": "running",
        "rabbitmq_consumer": "active background task",
        "storage_destinations": ["PostgreSQL", "Graylog GELF UDP"]
    }


if __name__ == "__main__":
    import uvicorn
    port = getattr(settings, "PORT", 8000)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
