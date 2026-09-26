"""مقادیر ثابت دامنه‌ی سامانه که بین چند ماژول مشترک است."""
from typing import Optional

# نوع پست/فیدر از نظر جهت انرژی
CONSUMER = "consumer"   # مصرف‌کننده
PRODUCER = "producer"   # تولیدکننده (مثل پنل خورشیدی)

_PRODUCER_ALIASES = {"producer", "generator", "production", "تولید", "تولیدی", "تولیدکننده", "تولید کننده"}
_CONSUMER_ALIASES = {"consumer", "consumption", "load", "مصرف", "مصرفی", "مصرف‌کننده", "مصرف کننده"}


def normalize_energy_role(value: Optional[str]) -> Optional[str]:
    """تبدیل مقادیر آزاد (Producer، «تولیدکننده»، ...) به consumer / producer."""
    if value is None:
        return None
    text = str(value).strip().lower().replace("‌", "")
    if not text:
        return None
    if text in {a.replace("‌", "") for a in _PRODUCER_ALIASES}:
        return PRODUCER
    if text in {a.replace("‌", "") for a in _CONSUMER_ALIASES}:
        return CONSUMER
    raise ValueError("نوع باید consumer (مصرف‌کننده) یا producer (تولیدکننده) باشد.")


# وضعیت بار فیدر/لینک نسبت به جریان مجاز
STATUS_NORMAL = "normal"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_UNKNOWN = "unknown"
LOAD_STATUSES = (STATUS_NORMAL, STATUS_WARNING, STATUS_CRITICAL, STATUS_UNKNOWN)

# صفحه‌های پنل که ادمین می‌تواند دسترسی هر حساب به آن‌ها را محدود کند
PAGES = {
    "dashboard": "داشبورد",
    "map": "نقشه",
    "locations": "مکان‌ها",
    "posts": "پست‌ها",
    "feeders": "فیدرها",
    "links": "لینک‌ها",
    "telemetry": "داده‌های زنده و نمودارها",
    "reports": "گزارش‌ها",
    "audit_logs": "لاگ‌ها",
}
