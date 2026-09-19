"""
Module: modules/base.py
توضیحات: تعاریف کلاس‌های پایه (Abstract Base Class) و مدل‌های اعتبارسنجی (Pydantic Models)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


# =====================================================================
# 1. انوع کانال‌های ارسال اعلان (Enums)
# =====================================================================
class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    ALL = "all"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# =====================================================================
# 2. طرح‌واره و ساختار پیام دریافتی از صف (Pydantic Schema)
# =====================================================================
class NotificationPayload(BaseModel):
    """
    اسکیمای پیام استاندارد که از صف RabbitMQ دریافت می‌شود.
    """
    channel: NotificationChannel = Field(
        default=NotificationChannel.ALL,
        description="کانال ارسال (sms, email, all)"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="عنوان اعلان یا موضوع ایمیل"
    )
    message: str = Field(
        ...,
        min_length=1,
        description="متن پیام اعلان"
    )
    phone_numbers: Optional[List[str]] = Field(
        default_factory=list,
        description="لیست شماره تلفن‌های گیرنده پیامک"
    )
    email_addresses: Optional[List[EmailStr]] = Field(
        default_factory=list,
        description="لیست ایمیل‌های گیرنده"
    )
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL,
        description="سطح اولویت یا حساسیت هشدار"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="اطلاعات متادیتا (مانند device_id, station_id, feeder_code و ...)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "channel": "all",
                "title": "هشدار افت ولتاژ فیدر",
                "message": "ولتاژ در ایستگاه تبریز از حد مجاز کمتر است.",
                "phone_numbers": ["09141234567"],
                "email_addresses": ["admin@example.com"],
                "priority": "high",
                "metadata": {"station_id": 12, "voltage": 185.4}
            }
        }


# =====================================================================
# 3. کلاس پایه انتزاعی ارائه‌دهنده‌ها (Abstract Base Provider)
# =====================================================================
class BaseNotificationProvider(ABC):
    """
    کلاس پایه انتزاعی؛ تمامی سرویس‌های ارسال (ایمیل، پیامک و ...)
    باید از این کلاس ارث‌بری کرده و متد send را پیاده‌سازی کنند.
    """

    @abstractmethod
    async def send(self, *args: Any, **kwargs: Any) -> bool:
        """
        ارسال اعلان به صورت Async.
        در صورت موفقیت باید True و در صورت بروز خطا False برگرداند.
        """
        pass
