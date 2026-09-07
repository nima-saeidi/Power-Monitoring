import logging
from email.message import EmailMessage
import aiosmtplib
from core.config import settings

logger = logging.getLogger("EmailProvider")

class EmailProvider:
    @staticmethod
    async def send_email(to_emails: list[str], subject: str, body: str) -> bool:
        if not to_emails or not settings.SMTP_USER:
            logger.warning("No recipient or SMTP not configured.")
            return False

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = ", ".join(to_emails)
        message["Subject"] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_USE_TLS,
            )
            logger.info(f"Email sent successfully to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
