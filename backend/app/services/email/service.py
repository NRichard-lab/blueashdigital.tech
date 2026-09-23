import smtplib
import socket

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.secrets import decrypt_secret, encrypt_secret
from app.models.email_settings import EmailProviderType, EmailSettings, EmailStatus
from app.services.email.base import EmailMessage, EmailProvider
from app.services.email.gmail import GmailProvider
from app.services.email.hostinger import HostingerProvider
from app.services.email.templates import test_email


class EmailDeliveryError(Exception):
    def __init__(self, message: str = "Unable to send email.") -> None:
        super().__init__(message)
        self.public_message = message


def _provider_from_settings(settings: EmailSettings) -> EmailProvider:
    if settings.provider == EmailProviderType.GMAIL:
        if not settings.email_address or not settings.encrypted_app_password:
            raise EmailDeliveryError("Gmail is not configured.")
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
    if settings.provider == EmailProviderType.HOSTINGER:
        if not settings.smtp_username or not settings.from_email or not settings.encrypted_smtp_password:
            raise EmailDeliveryError("Hostinger Email is not configured.")
        try:
            smtp_password = decrypt_secret(settings.encrypted_smtp_password)
        except Exception as exc:
            raise EmailDeliveryError("Email secret could not be decrypted.") from exc
        return HostingerProvider(
            smtp_username=settings.smtp_username,
            smtp_password=smtp_password,
            from_email=settings.from_email,
            from_name=settings.from_name or "Blue Ash Digital",
            reply_to=settings.reply_to,
            smtp_port=settings.smtp_port or 465,
            smtp_security=settings.smtp_security or "SSL_TLS",
        )
    raise EmailDeliveryError("Email provider is not supported.")


def _auth_error_message(settings: EmailSettings) -> str:
    if settings.provider == EmailProviderType.HOSTINGER:
        return "Unable to authenticate with Hostinger Email."
    return "Unable to authenticate with Gmail. Check the email address and App Password."


def _send_error_message(settings: EmailSettings, exc: Exception) -> str:
    if settings.provider == EmailProviderType.HOSTINGER:
        if app_settings.smtp_host and not app_settings.is_production:
            return "Unable to send email."
        if isinstance(exc, (TimeoutError, socket.gaierror, ConnectionError, OSError)):
            return "Unable to connect to smtp.hostinger.com."
        if isinstance(exc, smtplib.SMTPSenderRefused):
            return "Hostinger rejected the configured sender address."
        return "Unable to send email with Hostinger Email."
    return "Unable to send email with the configured provider."


def ensure_local_development_mailbox(db: Session) -> None:
    if app_settings.is_production or not app_settings.smtp_host:
        return
    row = get_active_email_settings(db)
    if row is None:
        row = EmailSettings()
        db.add(row)
    row.provider = EmailProviderType.HOSTINGER
    row.smtp_username = app_settings.smtp_username or "local-dev"
    row.encrypted_smtp_password = encrypt_secret(app_settings.smtp_password or "local-dev-mailbox")
    row.from_email = app_settings.email_from
    row.from_name = row.from_name or "Blue Ash Digital"
    row.smtp_port = app_settings.smtp_port
    row.smtp_security = "STARTTLS"
    row.enabled = True
    row.status = EmailStatus.CONFIGURED
    db.commit()


def get_active_email_settings(db: Session) -> EmailSettings | None:
    return db.scalar(select(EmailSettings).order_by(EmailSettings.created_at.asc()).limit(1))


def send_configured_email(db: Session, message: EmailMessage) -> None:
    settings = get_active_email_settings(db)
    if not settings or not settings.enabled:
        raise EmailDeliveryError("Email service is currently disabled.")
    try:
        _provider_from_settings(settings).send_email(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailDeliveryError(_auth_error_message(settings)) from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError(_send_error_message(settings, exc)) from exc


def test_configured_email(db: Session, recipient: str) -> None:
    settings = get_active_email_settings(db)
    if not settings or not settings.enabled:
        raise EmailDeliveryError("Email service is currently disabled.")
    try:
        provider = _provider_from_settings(settings)
        provider.test_connection()
        provider.send_email(test_email(to=recipient))
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailDeliveryError(_auth_error_message(settings)) from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        raise EmailDeliveryError(_send_error_message(settings, exc)) from exc
