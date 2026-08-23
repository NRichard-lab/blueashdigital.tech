import smtplib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.secrets import decrypt_secret
from app.models.email_settings import EmailProviderType, EmailSettings
from app.services.email.base import EmailMessage, EmailProvider
from app.services.email.gmail import GmailProvider


class EmailDeliveryError(Exception):
    def __init__(self, message: str = "Unable to send email.") -> None:
        super().__init__(message)
        self.public_message = message


def _provider_from_settings(settings: EmailSettings) -> EmailProvider:
    if settings.provider != EmailProviderType.GMAIL:
        raise EmailDeliveryError("Email provider is not supported.")
    if not settings.email_address or not settings.encrypted_app_password:
        raise EmailDeliveryError("Email is not configured.")
    try:
        app_password = decrypt_secret(settings.encrypted_app_password)
    except Exception as exc:
        raise EmailDeliveryError("Email secret could not be decrypted.") from exc
    return GmailProvider(
        email_address=settings.email_address,
        app_password=app_password,
        from_name=settings.from_name or "Application Portal",
        reply_to=settings.reply_to,
    )


def get_active_email_settings(db: Session) -> EmailSettings | None:
    return db.scalar(select(EmailSettings).order_by(EmailSettings.created_at.asc()).limit(1))


def send_configured_email(db: Session, message: EmailMessage) -> None:
    settings = get_active_email_settings(db)
    if not settings or not settings.enabled:
        raise EmailDeliveryError("Email service is currently disabled.")
    try:
        _provider_from_settings(settings).send_email(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailDeliveryError("Unable to authenticate with Gmail. Check the email address and App Password.") from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError("Unable to send email with the configured provider.") from exc


def test_configured_email(db: Session, recipient: str) -> None:
    settings = get_active_email_settings(db)
    if not settings or not settings.enabled:
        raise EmailDeliveryError("Email service is currently disabled.")
    try:
        provider = _provider_from_settings(settings)
        provider.test_connection()
        provider.send_email(__import__("app.services.email.templates", fromlist=["test_email"]).test_email(to=recipient))
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailDeliveryError("Unable to authenticate with Gmail. Check the email address and App Password.") from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError("Unable to send test email with Gmail.") from exc
