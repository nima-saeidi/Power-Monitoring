import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
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
        log_dir: str = "logs",
        app_name: str = "power_monitoring",
        enable_console: bool = True,
        enable_file: bool = True,
        enable_graylog: bool = True,
        graylog_host: str = None,
        graylog_port: int = 12201,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5
) -> logging.Logger:
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

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

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    if enable_file:
        general_log_file = log_path / f"{app_name}.log"
        file_handler = RotatingFileHandler(
            general_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        error_log_file = log_path / f"{app_name}_error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)

        daily_log_file = log_path / f"{app_name}_daily.log"
        daily_handler = TimedRotatingFileHandler(
            daily_log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(file_formatter)
        daily_handler.suffix = "%Y-%m-%d"
        logger.addHandler(daily_handler)

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
    log_dir=getattr(settings, "LOG_DIR", "logs"),
    app_name="power_monitoring",
    enable_console=True,
    enable_file=True,
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
