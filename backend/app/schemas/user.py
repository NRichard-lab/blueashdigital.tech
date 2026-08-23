import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import Role


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    role: Role
    enabled: bool
    mfa_enabled: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class CurrentUser(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    display_name: str
    role: Role
    mfa_enabled: bool = False

    model_config = {"from_attributes": True}

