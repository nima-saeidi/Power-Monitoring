import logging
import httpx
from core.config import settings

logger = logging.getLogger("SMSProvider")


class SMSProvider:
    @staticmethod
    async def send_sms(phone_numbers: list[str], message: str) -> bool:
        if not phone_numbers or not settings.SMS_API_KEY:
            logger.warning("SMS configuration missing or no recipients.")
            return False

        # فرض بر این است که پنل پیامکی شما یک API RESTful دارد
        # مثال: https://api.sms-provider.com/send?api_key=...&to=...&msg=...
        api_url = "https://api.sms-provider.com/v1/send"

        async with httpx.AsyncClient() as client:
            success = True
            for phone in phone_numbers:
                try:
                    payload = {
                        "api_key": settings.SMS_API_KEY,
                        "line": settings.SMS_LINE_NUMBER,
                        "to": phone,
                        "text": message
                    }
                    response = await client.post(api_url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    logger.info(f"SMS sent to {phone}")
                except Exception as e:
                    logger.error(f"Failed to send SMS to {phone}: {e}")
                    success = False
            return success
