import smtplib
import ssl
from email.message import EmailMessage as SmtpMessage

from app.services.email.base import EmailMessage, EmailProvider


class GmailProvider(EmailProvider):
    host = "smtp.gmail.com"
    port = 587

    def __init__(self, *, email_address: str, app_password: str, from_name: str, reply_to: str | None) -> None:
        self.email_address = email_address
        self.app_password = app_password
        self.from_name = from_name
        self.reply_to = reply_to

    def _smtp(self) -> smtplib.SMTP:
        client = smtplib.SMTP(self.host, self.port, timeout=20)
        client.starttls(context=ssl.create_default_context())
        client.login(self.email_address, self.app_password)
        return client

    def send_email(self, message: EmailMessage) -> None:
        smtp_message = SmtpMessage()
        smtp_message["Subject"] = message.subject
        smtp_message["From"] = f"{self.from_name} <{self.email_address}>"
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
