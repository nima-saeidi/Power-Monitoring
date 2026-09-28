import asyncio
import json
import logging
import os
import sys
from pathlib import Path
import aio_pika

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from core.config import settings
except ModuleNotFoundError:
    from config import settings

from handlers import handle_db_write_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("postgres_storage_worker")

# Ship every logger's records to Graylog (root logger, not just this one) -
# ops has no server access, only the Graylog port. Never fatal on failure.
try:
    import graypy
    _gelf_handler = graypy.GELFUDPHandler(
        os.getenv("GRAYLOG_HOST", "graylog"),
        int(os.getenv("GRAYLOG_PORT", "12201")),
        debugging_fields=True,
        extra_fields=True,
    )
    _gelf_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(_gelf_handler)
except Exception as _graylog_err:
    logger.warning(f"Could not attach Graylog handler: {_graylog_err}")


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False, ignore_processed=True):
        try:
            payload = json.loads(message.body.decode("utf-8"))
            routing_key = message.routing_key or "unknown"
            logger.info(f"Processing event from [{routing_key}]")
            logger.debug(f"Payload: {payload}")

            await handle_db_write_event(payload)
            logger.info(f"Successfully processed event: {payload.get('event_type', 'N/A')}")

        except json.JSONDecodeError:
            logger.error("Failed to decode message JSON. Sending to DLQ.")
            raise
        except Exception as e:
            logger.exception(f"Unhandled error processing message: {e}")
            raise


async def _declare_main_queue_with_dlq(connection, channel, queue_name: str):
    dlx_name = f"{queue_name}.dlx"
    dlq_name = f"{queue_name}.dlq"
    try:
        dlx_exchange = await channel.declare_exchange(dlx_name, aio_pika.ExchangeType.FANOUT, durable=True)
        dlq = await channel.declare_queue(dlq_name, durable=True)
        await dlq.bind(dlx_exchange)
        queue = await channel.declare_queue(
            queue_name, durable=True, arguments={"x-dead-letter-exchange": dlx_name}
        )
        return queue, channel
    except aio_pika.exceptions.ChannelClosed:
        logger.error(
            f"Queue '{queue_name}' already exists with incompatible arguments. "
            "Falling back WITHOUT dead-letter support; delete the queue manually once to enable DLQ."
        )
        fresh_channel = await connection.channel()
        await fresh_channel.set_qos(prefetch_count=10)
        queue = await fresh_channel.declare_queue(queue_name, durable=True)
        return queue, fresh_channel


async def run_worker() -> None:
    logger.info("Starting Postgres Storage Worker...")

    while True:
        try:
            connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                client_properties={"connection_name": "postgres_storage_consumer"}
            )

            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)

                queue, channel = await _declare_main_queue_with_dlq(connection, channel, "db.settings.write")

                exchange = await channel.declare_exchange(
                    "power_monitoring_events",
                    type=aio_pika.ExchangeType.TOPIC,
                    durable=True,
                )

                await queue.bind(exchange, routing_key="db.settings.*")
                await queue.bind(exchange, routing_key="db.users.*")
                await queue.bind(exchange, routing_key="db.telemetry.*")

                logger.info("Worker is ready and listening on queue 'db.settings.write'...")

                await queue.consume(process_message)

                stop_event = asyncio.Event()
                await stop_event.wait()

        except asyncio.CancelledError:
            logger.info("Worker task cancelled. Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"RabbitMQ connection lost/failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Postgres Storage Worker stopped by user.")
