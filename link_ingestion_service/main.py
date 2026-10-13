import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from modules.scheduler import LinkIngestionScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("link_ingestion_service")

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


async def main():
    scheduler = LinkIngestionScheduler()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # Windows dev machines
            pass

    await scheduler.start()
    try:
        await stop_event.wait()
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
