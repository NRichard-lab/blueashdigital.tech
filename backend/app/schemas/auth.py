from pydantic import BaseModel, Field
from pydantic import EmailStr


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class PasswordResetRequestCreate(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)


class PasswordResetComplete(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class EmailMfaRequest(BaseModel):
    email: EmailStr

