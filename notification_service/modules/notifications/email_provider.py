import logging
from email.message import EmailMessage
from typing import List, Optional
import aiosmtplib
from core.config import settings
from modules.notifications.base import BaseNotificationProvider

logger = logging.getLogger("EmailProvider")

class EmailProvider(BaseNotificationProvider):
    async def send(self, to_emails: List[str], subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if not to_emails:
            logger.warning("No recipient email addresses provided.")
            return False

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials are not configured in settings. Skipping email send.")
            return False

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = ", ".join(to_emails)
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_USE_TLS,
                timeout=15.0
            )
            logger.info(f"✅ Email successfully sent to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_emails}: {e}")
            return False
