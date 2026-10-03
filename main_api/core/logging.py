import logging
import sys
import os
from main_api.core.config import settings

try:
    import graypy

    GRAYPY_AVAILABLE = True
except ImportError:
    GRAYPY_AVAILABLE = False


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno,
                                   self.grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + self.reset)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(
        log_level: str = "INFO",
        service_name: str = "main_api",
        enable_console: bool = True,
        enable_graylog: bool = True,
        graylog_host: str = None,
        graylog_port: int = 12201
) -> logging.Logger:
    # Attach to the ROOT logger, not a named "power_monitoring" one: almost
    # every module in this codebase calls logging.getLogger(__name__) or
    # logging.getLogger("main_api"), and neither propagates to a logger named
    # "power_monitoring" - only to their own dotted-name ancestors, which
    # bottom out at root. Handlers on a non-root "power_monitoring" logger
    # were silently only ever catching the handful of loggers built via
    # get_logger() below, never the app's real operational logs.
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    if enable_graylog:
        if GRAYPY_AVAILABLE:
            target_host = graylog_host or getattr(settings, "GRAYLOG_HOST", os.getenv("GRAYLOG_HOST", "graylog"))
            target_port = int(getattr(settings, "GRAYLOG_PORT", os.getenv("GRAYLOG_PORT", graylog_port)))
            try:
                gelf_handler = graypy.GELFUDPHandler(
                    target_host,
                    target_port,
                    debugging_fields=True,
                    extra_fields=True
                )
                gelf_handler.setLevel(logging.INFO)
                logger.addHandler(gelf_handler)
            except Exception as e:
                logger.warning(f"Could not connect to Graylog: {e}")
        else:
            logger.warning("graypy package is not installed. Graylog logging disabled.")

    return logger


app_logger = setup_logging(
    log_level=getattr(settings, "LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_graylog=getattr(settings, "GRAYLOG_ENABLED", True)
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"power_monitoring.{name}")


modbus_logger = get_logger("modbus")
api_logger = get_logger("api")
auth_logger = get_logger("auth")
db_logger = get_logger("database")
scheduler_logger = get_logger("scheduler")
audit_logger = get_logger("audit")
