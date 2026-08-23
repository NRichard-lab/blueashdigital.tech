from app.core.config import settings
from app.services.email.base import EmailMessage


def password_reset_email(*, to: str, reset_url: str, expires_minutes: int) -> EmailMessage:
    subject = f"{settings.app_name} password reset"
    text = (
        f"Reset your {settings.app_name} password using this link:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {expires_minutes} minutes. If you did not request this, you can ignore this email."
    )
    html = (
        f"<p>Reset your <strong>{settings.app_name}</strong> password using the link below.</p>"
        f"<p><a href=\"{reset_url}\">Reset password</a></p>"
        f"<p>This link expires in {expires_minutes} minutes. If you did not request this, you can ignore this email.</p>"
    )
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)


def email_mfa_code(*, to: str, code: str, expires_minutes: int) -> EmailMessage:
    subject = f"{settings.app_name} verification code"
    text = f"Your verification code is {code}. It expires in {expires_minutes} minutes."
    html = f"<p>Your verification code is <strong>{code}</strong>.</p><p>It expires in {expires_minutes} minutes.</p>"
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)


def account_created_email(*, to: str, username: str, setup_url: str) -> EmailMessage:
    subject = f"Your {settings.app_name} account"
    text = f"Your account is ready.\n\nPortal: {settings.frontend_origin}\nUsername: {username}\nSet your password: {setup_url}"
    html = (
        "<p>Your account is ready.</p>"
        f"<p><strong>Portal:</strong> <a href=\"{settings.frontend_origin}\">{settings.frontend_origin}</a></p>"
        f"<p><strong>Username:</strong> {username}</p>"
        f"<p><a href=\"{setup_url}\">Set your password</a></p>"
    )
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)


def security_notification_email(*, to: str, title: str, message: str) -> EmailMessage:
    subject = f"{settings.app_name}: {title}"
    text = message
    html = f"<p>{message}</p>"
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)


def test_email(*, to: str) -> EmailMessage:
    subject = f"{settings.app_name} test email"
    text = "This is a test email from your portal email settings."
    html = "<p>This is a test email from your portal email settings.</p>"
    return EmailMessage(to=to, subject=subject, text_body=text, html_body=html)
