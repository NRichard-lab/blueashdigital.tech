import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.email_settings import EmailProviderType, EmailStatus


class PermissionRead(BaseModel):
    key: str
    label: str
    group: str
    description: str = ""


class RoleRead(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str
    system: bool
    users_count: int
    permission_keys: list[str]


class RoleListResponse(BaseModel):
    roles: list[RoleRead]
    permissions: list[PermissionRead]
    critical_permissions: list[str]


class RoleUpdate(BaseModel):
    permission_keys: list[str] = Field(default_factory=list)


class EmailSettingsRead(BaseModel):
    provider: EmailProviderType = EmailProviderType.GMAIL
    email_address: EmailStr | None = None
    smtp_username: EmailStr | None = None
    from_email: EmailStr | None = None
    from_name: str | None = None
    reply_to: EmailStr | None = None
    enabled: bool = False
    status: EmailStatus = EmailStatus.NOT_CONFIGURED
    has_app_password: bool = False
    has_smtp_password: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_security: str = "STARTTLS"
    encryption: str = "STARTTLS"
    last_test_at: datetime | None = None
    last_test_result: str | None = None
    last_error: str | None = None


class EmailSettingsUpdate(BaseModel):
    provider: EmailProviderType = EmailProviderType.GMAIL
    email_address: EmailStr | None = None
    app_password: str | None = Field(default=None, min_length=8, max_length=256)
    smtp_username: EmailStr | None = None
    smtp_password: str | None = Field(default=None, min_length=8, max_length=256)
    from_email: EmailStr | None = None
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_security: str = Field(default="SSL_TLS", pattern="^(SSL_TLS|STARTTLS)$")
    from_name: str = Field(min_length=2, max_length=160)
    reply_to: EmailStr | None = None
    enabled: bool = False


class EmailTestRequest(BaseModel):
    recipient: EmailStr


class EmailTestResponse(BaseModel):
    status: EmailStatus
    message: str


class AuthenticationSettingsRead(BaseModel):
    idle_timeout_minutes: int
    absolute_timeout_minutes: int
    mfa_code_expiration_minutes: int
    mfa_max_attempts: int
    mfa_resend_delay_seconds: int


class AuthenticationSettingsUpdate(BaseModel):
    idle_timeout_minutes: int = Field(default=30, ge=5, le=480)
    absolute_timeout_minutes: int = Field(default=480, ge=30, le=1440)
    mfa_code_expiration_minutes: int = Field(default=10, ge=2, le=15)
    mfa_max_attempts: int = Field(default=5, ge=3, le=10)
    mfa_resend_delay_seconds: int = Field(default=60, ge=30, le=300)
