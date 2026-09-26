from slowapi import Limiter
from slowapi.util import get_remote_address

from main_api.core.config import settings

# محدودیت پیش‌فرض برای همه‌ی روت‌ها (به ازای هر IP)؛ روت‌های حساس با
# دکوریتور @limiter.limit(...) محدودیت سخت‌گیرانه‌تری می‌گیرند.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
)

# محدودیت‌های روت‌های حساس (به ازای هر IP)
LOGIN_LIMIT = "5/minute;20/hour"
REGISTER_ADMIN_LIMIT = "3/hour"
FORGOT_PASSWORD_LIMIT = "3/minute;10/hour"
VERIFY_CODE_LIMIT = "5/minute;20/hour"
RESET_PASSWORD_LIMIT = "5/minute;20/hour"
CHANGE_PASSWORD_LIMIT = "5/minute"
EXPORT_LIMIT = "10/minute"
IMPORT_LIMIT = "5/minute"
COMMAND_LIMIT = "10/minute"
