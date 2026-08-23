from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str


class EmailProvider:
    def send_email(self, message: EmailMessage) -> None:
        raise NotImplementedError

    def test_connection(self) -> None:
        raise NotImplementedError
