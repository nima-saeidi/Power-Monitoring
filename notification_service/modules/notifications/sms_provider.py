import asyncio
import logging
from typing import List

import httpx

from core.config import settings
from modules.notifications.base import BaseNotificationProvider

logger = logging.getLogger("SMSProvider")

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 2.0


class SMSProvider(BaseNotificationProvider):
    async def send(self, phone_numbers: List[str], message: str) -> bool:
        if not phone_numbers:
            logger.warning("No recipient phone numbers provided.")
            return False

        if not settings.SMS_API_KEY:
            logger.warning("SMS_API_KEY is missing in settings. Skipping SMS send.")
            return False

        success = True
        async with httpx.AsyncClient(timeout=10.0) as client:
            for phone in phone_numbers:
                if not await self._send_one(client, phone, message):
                    success = False
        return success

    async def _send_one(self, client: httpx.AsyncClient, phone: str, message: str) -> bool:
        payload = {
            "api_key": settings.SMS_API_KEY,
            "line": settings.SMS_LINE_NUMBER,
            "to": phone,
            "text": message,
        }
        last_error: Exception | None = None
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                response = await client.post(settings.SMS_API_URL, json=payload)
                response.raise_for_status()
                logger.info(f"✅ SMS successfully sent to {phone}")
                return True
            except httpx.HTTPStatusError as e:
                # A 4xx (bad number, bad request) will never succeed on retry;
                # only a 5xx from the provider is worth retrying.
                logger.error(f"❌ SMS API returned error for {phone}: {e.response.status_code} - {e.response.text}")
                if e.response.status_code < 500:
                    return False
                last_error = e
            except Exception as e:
                last_error = e

            if attempt < _RETRY_ATTEMPTS:
                delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    f"⚠️ SMS send attempt {attempt}/{_RETRY_ATTEMPTS} to {phone} failed: "
                    f"{last_error}. Retrying in {delay:.0f}s..."
                )
                await asyncio.sleep(delay)

        logger.error(f"❌ Failed to send SMS to {phone} after {_RETRY_ATTEMPTS} attempts: {last_error}")
        return False
