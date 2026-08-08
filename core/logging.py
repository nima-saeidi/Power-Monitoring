import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional
from core.config import settings


class CustomFormatter(logging.Formatter):
    """فرمت دهنده سفارشی با رنگ برای کنسول"""
    
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
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "power_monitoring",
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    راه‌اندازی سیستم لاگینگ
    
    Args:
        log_level: سطح لاگ (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: مسیر ذخیره فایل‌های لاگ
        app_name: نام برنامه
        enable_console: فعال‌سازی خروجی کنسول
        enable_file: فعال‌سازی ذخیره در فایل
        max_bytes: حداکثر حجم هر فایل لاگ
        backup_count: تعداد فایل‌های پشتیبان
        
    Returns:
        Logger پیکربندی شده
    """
    
    # ایجاد پوشه لاگ
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # تنظیم logger اصلی
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()  # پاکسازی handlers قبلی
    
    # فرمت استاندارد برای فایل
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler کنسول
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)
    
    # Handler فایل با Rotation بر اساس حجم
    if enable_file:
        # فایل لاگ عمومی
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
        
        # فایل لاگ خطاها
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
        
        # فایل لاگ روزانه
        daily_log_file = log_path / f"{app_name}_daily.log"
        daily_handler = TimedRotatingFileHandler(
            daily_log_file,
            when="midnight",
            interval=1,
            backupCount=30,  # نگهداری 30 روز
            encoding="utf-8"
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(file_formatter)
        daily_handler.suffix = "%Y-%m-%d"
        logger.addHandler(daily_handler)
    
    return logger


# Logger اصلی برنامه
app_logger = setup_logging(
    log_level=getattr(settings, "LOG_LEVEL", "INFO"),
    log_dir="logs",
    app_name="power_monitoring"
)


def get_logger(name: str) -> logging.Logger:
    """دریافت logger با نام مشخص"""
    return logging.getLogger(f"power_monitoring.{name}")


# Loggerهای اختصاصی برای بخش‌های مختلف
modbus_logger = get_logger("modbus")
api_logger = get_logger("api")
auth_logger = get_logger("auth")
db_logger = get_logger("database")
scheduler_logger = get_logger("scheduler")
audit_logger = get_logger("audit")
