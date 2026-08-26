from datetime import datetime

from pydantic import BaseModel, Field
from pydantic import EmailStr

from app.schemas.user import CurrentUser


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    return_to: str | None = Field(default=None, max_length=2048)


class PasswordResetRequestCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)


class PasswordResetComplete(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class EmailMfaRequest(BaseModel):
    email: EmailStr


class EmailMfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaRequiredResponse(BaseModel):
    status: str = "MFA_REQUIRED"
    masked_email: str
    expires_at: datetime
    resend_available_at: datetime | None = None


class LoginResponse(BaseModel):
    status: str = "AUTHENTICATED"
    user: CurrentUser | None = None
    masked_email: str | None = None
    expires_at: datetime | None = None
    resend_available_at: datetime | None = None
    return_to: str | None = None

