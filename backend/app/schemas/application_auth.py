import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import Role


class ApplicationTokenExchangeRequest(BaseModel):
    code: str = Field(min_length=20, max_length=256)
    code_verifier: str = Field(min_length=43, max_length=128)
    redirect_uri: str = Field(min_length=1, max_length=2048)


class ApplicationTokenExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    idle_expires_at: datetime
    absolute_expires_at: datetime


class ApplicationTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class ApplicationIntrospectionResponse(BaseModel):
    active: bool
    user_id: uuid.UUID | None = None
    username: str | None = None
    email: str | None = None
    display_name: str | None = None
    role: Role | None = None
    permissions: list[str] | None = None
    application_id: uuid.UUID | None = None
    application_slug: str | None = None
    idle_expires_at: datetime | None = None
    absolute_expires_at: datetime | None = None
    return_path: str | None = None
