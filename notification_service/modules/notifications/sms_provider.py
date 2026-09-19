import logging
from typing import List
import httpx
from core.config import settings
from modules.notifications.base import BaseNotificationProvider

logger = logging.getLogger("SMSProvider")

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
                payload = {
                    "api_key": settings.SMS_API_KEY,
                    "line": settings.SMS_LINE_NUMBER,
                    "to": phone,
                    "text": message
                }
                try:
                    response = await client.post(settings.SMS_API_URL, json=payload)
                    response.raise_for_status()
                    logger.info(f"✅ SMS successfully sent to {phone}")
                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ SMS API returned error for {phone}: {e.response.status_code} - {e.response.text}")
                    success = False
                except Exception as e:
                    logger.error(f"❌ Failed to send SMS to {phone}: {e}")
                    success = False

        return success
