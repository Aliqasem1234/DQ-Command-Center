import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.is_mock = not (settings.SMTP_HOST and settings.SMTP_USER)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        if self.is_mock:
            # Never log email body/links here - in mock mode this is the
            # only place a password-reset or email-verification token
            # would otherwise end up in plaintext in application logs.
            logger.info(f"MOCK EMAIL: would send '{subject}' to {to_email} (SMTP not configured)")
            return True

        try:
            await asyncio.to_thread(self._send_smtp, to_email, subject, body, html_body)
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str],
    ) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message.attach(MIMEText(body, "plain"))
        if html_body:
            message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], message.as_string())

    async def send_verification_email(self, to_email: str, token: str) -> bool:
        verify_url = f"{settings.CORS_ORIGINS.split(',')[0].strip()}/verify-email?token={token}"
        subject = f"Verify your email - {settings.APP_NAME}"
        body = f"""
Welcome to {settings.APP_NAME}!

Please verify your email address by clicking the link below:
{verify_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.
        """
        return await self.send_email(to_email, subject, body)

    async def send_password_reset_email(self, to_email: str, token: str) -> bool:
        reset_url = f"{settings.CORS_ORIGINS.split(',')[0].strip()}/reset-password?token={token}"
        subject = f"Reset your password - {settings.APP_NAME}"
        body = f"""
You requested a password reset for {settings.APP_NAME}.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this, please ignore this email.
        """
        return await self.send_email(to_email, subject, body)


email_service = EmailService()
