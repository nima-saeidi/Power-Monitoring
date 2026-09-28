import asyncio
import logging
from email.message import EmailMessage
from typing import List, Optional

import aiosmtplib

from core.config import settings
from modules.notifications.base import BaseNotificationProvider

logger = logging.getLogger("EmailProvider")

# Most SMTP providers (Gmail included) start throttling or rejecting a message
# once its recipient count gets too high, and a single slow/failing SMTP
# transaction previously blocked every other recipient in the same batch.
# Chunking bounds both risks.
MAX_RECIPIENTS_PER_BATCH = 40

# All batches for one notification, plus every other notification the worker
# is processing concurrently (prefetch_count=10), used to share one small pool
# of SMTP connections instead of opening one per message - a burst of alerts
# (e.g. a whole substation going offline at once) would otherwise open dozens
# of simultaneous connections to the same provider and get rate-limited.
_SEND_CONCURRENCY = asyncio.Semaphore(5)

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 2.0


def _chunk(items: List[str], size: int) -> List[List[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


class EmailProvider(BaseNotificationProvider):
    async def send(self, to_emails: List[str], subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if not to_emails:
            logger.warning("No recipient email addresses provided.")
            return False

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials are not configured in settings. Skipping email send.")
            return False

        all_ok = True
        for batch in _chunk(to_emails, MAX_RECIPIENTS_PER_BATCH):
            if not await self._send_batch(batch, subject, body, html_body):
                all_ok = False
        return all_ok

    async def _send_batch(self, to_emails: List[str], subject: str, body: str,
                          html_body: Optional[str]) -> bool:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        # No real recipient address goes into a header: putting every recipient
        # in a shared To: (or even Bcc:, which most mail servers don't actually
        # strip before delivery) leaks everyone's address to everyone else in
        # the batch. The real envelope recipients are passed explicitly via
        # aiosmtplib's `recipients=` below (RCPT TO), independent of headers,
        # so each recipient only ever sees this generic placeholder.
        message["To"] = "Undisclosed recipients:;"
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        last_error: Optional[Exception] = None
        async with _SEND_CONCURRENCY:
            for attempt in range(1, _RETRY_ATTEMPTS + 1):
                try:
                    await aiosmtplib.send(
                        message,
                        sender=settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                        recipients=to_emails,
                        hostname=settings.SMTP_HOST,
                        port=settings.SMTP_PORT,
                        username=settings.SMTP_USER,
                        password=settings.SMTP_PASSWORD,
                        use_tls=settings.SMTP_PORT == 465,
                        start_tls=settings.SMTP_USE_TLS and settings.SMTP_PORT != 465,
                        timeout=15.0,
                    )
                    logger.info(f"✅ Email successfully sent to {len(to_emails)} recipient(s)")
                    return True
                except Exception as e:
                    last_error = e
                    if attempt < _RETRY_ATTEMPTS:
                        delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                        logger.warning(
                            f"⚠️ Email send attempt {attempt}/{_RETRY_ATTEMPTS} to "
                            f"{len(to_emails)} recipient(s) failed: {e}. Retrying in {delay:.0f}s..."
                        )
                        await asyncio.sleep(delay)

        logger.error(
            f"❌ Failed to send email to {len(to_emails)} recipient(s) after "
            f"{_RETRY_ATTEMPTS} attempts: {last_error}"
        )
        return False

    async def check_connection(self) -> bool:
        """One-shot startup connectivity check: connects and authenticates
        without sending a message, so a bad password or unreachable host is
        caught loudly at boot instead of silently on the first real alert."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning(
                "⚠️ SMTP credentials are not configured (SMTP_USER/SMTP_PASSWORD). "
                "All outgoing emails will be dlq silently skipped until this is fixed."
            )
            return False
        try:
            client = aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST, port=settings.SMTP_PORT, timeout=10.0,
                use_tls=settings.SMTP_PORT == 465,
            )
            async with client:
                if settings.SMTP_USE_TLS and settings.SMTP_PORT != 465:
                    await client.starttls()
                await client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            logger.info(f"✅ SMTP connectivity check passed ({settings.SMTP_HOST}:{settings.SMTP_PORT}).")
            return True
        except Exception as e:
            logger.error(
                f"❌ SMTP connectivity check FAILED for {settings.SMTP_HOST}:{settings.SMTP_PORT}: {e}. "
                "Outgoing emails will fail until this is fixed."
            )
            return False
