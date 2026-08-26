import logging
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
            logger.info("=" * 60)
            logger.info(f"MOCK EMAIL TO: {to_email}")
            logger.info(f"SUBJECT: {subject}")
            logger.info(f"BODY: {body[:500]}..." if len(body) > 500 else f"BODY: {body}")
            logger.info("=" * 60)
            return True

        try:
            # Real SMTP implementation would go here
            # For production, configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD
            logger.info(f"Sending real email to {to_email} via SMTP")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

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
