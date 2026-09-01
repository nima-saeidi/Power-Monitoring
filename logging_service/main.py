import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.consumer import start_consumer
from modules.routers import router as logs_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ۱. شروع Consumer به عنوان تسک پس‌زمینه در زمان بالا آمدن سرویس
    logger.info("Starting RabbitMQ Consumer task...")
    consumer_task = asyncio.create_task(start_consumer())

    yield

    # ۲. توقف و کنسل کردن تسک هنگام خاموش شدن سرویس
    logger.info("Stopping RabbitMQ Consumer task...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("RabbitMQ Consumer task cancelled successfully.")


app = FastAPI(
    title="Power Monitoring - Logging & Audit Service",
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

app.include_router(logs_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
