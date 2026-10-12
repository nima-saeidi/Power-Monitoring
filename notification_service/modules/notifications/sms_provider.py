import asyncio
import logging
import re
from typing import List, Optional

import httpx

from core.config import settings
from modules.notifications.base import BaseNotificationProvider
from modules.notifications.sms_gateways import BaseSMSGateway, SMSResult, build_sms_gateway

logger = logging.getLogger("SMSProvider")

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 2.0

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_IRAN_MOBILE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(phone: str) -> Optional[str]:
    """+989121234567 / 00989121234567 / 989121234567 / 9121234567 / ۰۹۱۲... -> 09121234567.
    Returns None for anything that is not a valid Iranian mobile number."""
    digits = re.sub(r"\D", "", str(phone).translate(_PERSIAN_DIGITS))
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits if _IRAN_MOBILE_RE.match(digits) else None


class SMSProvider(BaseNotificationProvider):
    def __init__(self, gateway: Optional[BaseSMSGateway] = None):
        self.gateway = gateway or build_sms_gateway()
        # A burst of alerts (a whole substation going offline at once) must not
        # open dozens of parallel requests to the panel and get rate-limited.
        self._concurrency = asyncio.Semaphore(max(1, settings.SMS_SEND_CONCURRENCY))

    def is_ready(self) -> bool:
        return settings.SMS_ENABLED and self.gateway.is_configured()

    async def send(self, phone_numbers: List[str], message: str) -> bool:
        if not phone_numbers:
            logger.warning("No recipient phone numbers provided.")
            return False

        if not settings.SMS_ENABLED:
            # Intentionally switched off: not a delivery failure, so don't
            # dead-letter the message (and re-send its email on replay).
            logger.info(f"SMS_ENABLED=false. Skipping SMS to {len(phone_numbers)} recipient(s).")
            return True

        if not self.gateway.is_configured():
            logger.warning(f"SMS gateway '{self.gateway.name}' is not configured. Skipping SMS send.")
            return False

        recipients = []
        for raw in phone_numbers:
            phone = normalize_phone(raw)
            if phone is None:
                logger.warning(f"Skipping invalid phone number: {raw!r}")
            elif phone not in recipients:
                recipients.append(phone)
        if not recipients:
            return False

        text = message
        if len(text) > settings.SMS_MAX_LENGTH:
            text = text[: settings.SMS_MAX_LENGTH - 1] + "…"

        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await asyncio.gather(*(self._send_one(client, p, text) for p in recipients))
        return all(results)

    async def _send_one(self, client: httpx.AsyncClient, phone: str, text: str) -> bool:
        result = SMSResult(success=False)
        async with self._concurrency:
            for attempt in range(1, _RETRY_ATTEMPTS + 1):
                try:
                    result = await self.gateway.send_one(client, phone, text)
                except Exception as e:
                    result = SMSResult(success=False, retryable=True, error=str(e))

                if result.success:
                    logger.info(f"✅ SMS sent to {phone} via '{self.gateway.name}' (id={result.provider_message_id})")
                    return True
                if not result.retryable:
                    break
                if attempt < _RETRY_ATTEMPTS:
                    delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        f"⚠️ SMS send attempt {attempt}/{_RETRY_ATTEMPTS} to {phone} failed: "
                        f"{result.error}. Retrying in {delay:.0f}s..."
                    )
                    await asyncio.sleep(delay)

        logger.error(f"❌ Failed to send SMS to {phone} via '{self.gateway.name}': {result.error}")
        return False
