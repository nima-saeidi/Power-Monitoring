from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.errors import install_error_handlers
from modules.telemetry.router import router as telemetry_router
from modules.telemetry.scheduler import TelemetryScheduler

logger = logging.getLogger(__name__)

scheduler = TelemetryScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Telemetry Service & Polling Scheduler...")

    try:
        await scheduler.start()
    except Exception as e:
        logger.error(f"❌ Failed to start Telemetry Scheduler: {e}", exc_info=True)

    yield

    logger.info("🛑 Shutting down Telemetry Service...")
    try:
        await scheduler.stop()
    except Exception as e:
        logger.error(f"❌ Error during scheduler shutdown: {e}", exc_info=True)


app = FastAPI(
    title="Telemetry Microservice",
    description="High-Performance Modbus Polling, InfluxDB Storage & Redis Publisher",
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

app.include_router(telemetry_router)