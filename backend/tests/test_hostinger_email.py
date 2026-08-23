from app.services.email.base import EmailMessage
from app.services.email.hostinger import HostingerProvider


class RecordingSMTP:
    instances: list["RecordingSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int = 20, context: object | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.started_tls = False
        self.login_credentials: tuple[str, str] | None = None
        self.sent_messages = []
        RecordingSMTP.instances.append(self)

    def starttls(self, *, context: object) -> None:
        self.started_tls = True
        self.context = context

    def login(self, username: str, password: str) -> None:
        self.login_credentials = (username, password)

    def send_message(self, message) -> None:
        self.sent_messages.append(message)

    def __enter__(self) -> "RecordingSMTP":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def test_hostinger_uses_ssl_and_configured_sender(monkeypatch) -> None:
    RecordingSMTP.instances = []
    monkeypatch.setattr("app.services.email.hostinger.smtplib.SMTP_SSL", RecordingSMTP)

    provider = HostingerProvider(
        smtp_username="realmailbox@blueashdigital.tech",
        smtp_password="mailbox-secret",
        from_email="donotreply@blueashdigital.tech",
        from_name="Blue Ash Digital",
        reply_to="support@blueashdigital.tech",
    )
    provider.send_email(
        EmailMessage(
            to="recipient@example.com",
            subject="Blue Ash Digital Email Test",
            text_body="Test email",
            html_body="<p>Test email</p>",
        )
    )

    client = RecordingSMTP.instances[0]
    message = client.sent_messages[0]
    assert client.host == "smtp.hostinger.com"
    assert client.port == 465
    assert not client.started_tls
    assert client.login_credentials == ("realmailbox@blueashdigital.tech", "mailbox-secret")
    assert message["From"] == "Blue Ash Digital <donotreply@blueashdigital.tech>"
    assert message["Reply-To"] == "support@blueashdigital.tech"


def test_hostinger_supports_starttls_fallback(monkeypatch) -> None:
    RecordingSMTP.instances = []
    monkeypatch.setattr("app.services.email.hostinger.smtplib.SMTP", RecordingSMTP)

    provider = HostingerProvider(
        smtp_username="realmailbox@blueashdigital.tech",
        smtp_password="mailbox-secret",
        from_email="donotreply@blueashdigital.tech",
        from_name="Blue Ash Digital",
        reply_to=None,
        smtp_port=587,
        smtp_security="STARTTLS",
    )
    provider.test_connection()

    client = RecordingSMTP.instances[0]
    assert client.host == "smtp.hostinger.com"
    assert client.port == 587
    assert client.started_tls
    assert client.login_credentials == ("realmailbox@blueashdigital.tech", "mailbox-secret")
