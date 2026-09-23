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
    monkeypatch.setattr("app.services.email.hostinger.settings.smtp_host", None)
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
    monkeypatch.setattr("app.services.email.hostinger.settings.smtp_host", None)
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


def test_development_smtp_host_uses_the_local_catcher(monkeypatch) -> None:
    RecordingSMTP.instances = []
    monkeypatch.setattr("app.services.email.hostinger.smtplib.SMTP", RecordingSMTP)
    monkeypatch.setattr("app.services.email.hostinger.settings.smtp_host", "mailpit")
    monkeypatch.setattr("app.services.email.hostinger.settings.smtp_port", 1025)
    monkeypatch.setattr("app.services.email.hostinger.settings.app_env", "development")

    provider = HostingerProvider(
        smtp_username="local-dev",
        smtp_password="local-dev-mailbox",
        from_email="no-reply@localhost",
        from_name="Blue Ash Digital",
        reply_to=None,
    )
    provider.send_email(
        EmailMessage(
            to="person@example.com",
            subject="Blue Ash Digital verification code",
            text_body="Your verification code is 000000.",
            html_body="<p>Your verification code is <strong>000000</strong>.</p>",
        )
    )

    client = RecordingSMTP.instances[0]
    assert client.host == "mailpit"
    assert client.port == 1025
    assert not client.started_tls
    assert client.login_credentials == ("local-dev", "local-dev-mailbox")


def test_production_ignores_a_local_smtp_host(monkeypatch) -> None:
    RecordingSMTP.instances = []
    monkeypatch.setattr("app.services.email.hostinger.smtplib.SMTP_SSL", RecordingSMTP)
    monkeypatch.setattr("app.services.email.hostinger.settings.smtp_host", "mailpit")
    monkeypatch.setattr("app.services.email.hostinger.settings.app_env", "production")

    provider = HostingerProvider(
        smtp_username="realmailbox@blueashdigital.tech",
        smtp_password="mailbox-secret",
        from_email="donotreply@blueashdigital.tech",
        from_name="Blue Ash Digital",
        reply_to=None,
    )
    provider.test_connection()

    client = RecordingSMTP.instances[0]
    assert client.host == "smtp.hostinger.com"
    assert client.port == 465
