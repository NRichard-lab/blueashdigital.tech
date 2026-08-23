import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EmailProviderType(str, enum.Enum):
    GMAIL = "gmail"
    HOSTINGER = "hostinger"


class EmailStatus(str, enum.Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    VERIFIED = "VERIFIED"
    ERROR = "ERROR"


class EmailSettings(Base):
    __tablename__ = "email_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[EmailProviderType] = mapped_column(Enum(EmailProviderType, name="email_provider_enum", values_callable=lambda enum_cls: [item.value for item in enum_cls]), nullable=False, default=EmailProviderType.GMAIL)
    email_address: Mapped[str | None] = mapped_column(String(320))
    encrypted_app_password: Mapped[str | None] = mapped_column(Text)
    smtp_username: Mapped[str | None] = mapped_column(String(320))
    encrypted_smtp_password: Mapped[str | None] = mapped_column(Text)
    from_email: Mapped[str | None] = mapped_column(String(320))
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=465)
    smtp_security: Mapped[str] = mapped_column(String(20), nullable=False, default="SSL_TLS")
    from_name: Mapped[str | None] = mapped_column(String(160))
    reply_to: Mapped[str | None] = mapped_column(String(320))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[EmailStatus] = mapped_column(Enum(EmailStatus, name="email_status_enum", values_callable=lambda enum_cls: [item.value for item in enum_cls]), nullable=False, default=EmailStatus.NOT_CONFIGURED)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_result: Mapped[str | None] = mapped_column(String(40))
    last_error: Mapped[str | None] = mapped_column(String(240))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailMfaChallenge(Base):
    __tablename__ = "email_mfa_challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ip_address: Mapped[str | None] = mapped_column(String(64))
