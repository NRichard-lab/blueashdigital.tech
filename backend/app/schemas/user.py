import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.models.user import Role
from app.services.permission_service import get_user_permission_keys


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    role: Role
    enabled: bool
    force_password_change: bool = False
    mfa_required: bool = False
    mfa_enabled: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    applications_assigned: int = 0
    application_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CurrentUser(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    role: Role
    mfa_enabled: bool = False
    permissions: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


def current_user_payload(user, db: Session) -> CurrentUser:
    permissions = sorted(get_user_permission_keys(db, user))
    payload = CurrentUser.model_validate(user)
    payload.permissions = permissions
    return payload


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    role: Role
    temporary_password: str = Field(min_length=12, max_length=256)
    enabled: bool = True
    mfa_required: bool = False
    application_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class UserUpdate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    role: Role
    enabled: bool
    mfa_required: bool = False
    application_ids: list[uuid.UUID] = Field(default_factory=list)


class PasswordResetRequest(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=256)
    force_password_change: bool = False
