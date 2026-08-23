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
    from_name: str | None = None
    reply_to: EmailStr | None = None
    enabled: bool = False
    status: EmailStatus = EmailStatus.NOT_CONFIGURED
    has_app_password: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    encryption: str = "STARTTLS"
    last_test_at: datetime | None = None
    last_test_result: str | None = None
    last_error: str | None = None


class EmailSettingsUpdate(BaseModel):
    provider: EmailProviderType = EmailProviderType.GMAIL
    email_address: EmailStr
    app_password: str | None = Field(default=None, min_length=8, max_length=256)
    from_name: str = Field(min_length=2, max_length=160)
    reply_to: EmailStr | None = None
    enabled: bool = False


class EmailTestRequest(BaseModel):
    recipient: EmailStr


class EmailTestResponse(BaseModel):
    status: EmailStatus
    message: str
