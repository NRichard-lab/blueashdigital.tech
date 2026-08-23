import smtplib
import ssl
from email.message import EmailMessage as SmtpMessage

from app.services.email.base import EmailMessage, EmailProvider


class HostingerProvider(EmailProvider):
    host = "smtp.hostinger.com"

    def __init__(
        self,
        *,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
        reply_to: str | None,
        smtp_port: int = 465,
        smtp_security: str = "SSL_TLS",
    ) -> None:
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        self.reply_to = reply_to
        self.smtp_port = smtp_port
        self.smtp_security = smtp_security

    def _smtp(self) -> smtplib.SMTP:
        context = ssl.create_default_context()
        if self.smtp_port == 587 or self.smtp_security == "STARTTLS":
            client = smtplib.SMTP(self.host, self.smtp_port, timeout=20)
            client.starttls(context=context)
        else:
            client = smtplib.SMTP_SSL(self.host, self.smtp_port, timeout=20, context=context)
        client.login(self.smtp_username, self.smtp_password)
        return client

    def send_email(self, message: EmailMessage) -> None:
        smtp_message = SmtpMessage()
        smtp_message["Subject"] = message.subject
        smtp_message["From"] = f"{self.from_name} <{self.from_email}>"
        smtp_message["To"] = message.to
        if self.reply_to:
            smtp_message["Reply-To"] = self.reply_to
        smtp_message.set_content(message.text_body)
        smtp_message.add_alternative(message.html_body, subtype="html")
        with self._smtp() as client:
            client.send_message(smtp_message)

    def test_connection(self) -> None:
        with self._smtp():
            return
