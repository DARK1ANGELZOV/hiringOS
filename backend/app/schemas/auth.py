from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    token_type: str = 'bearer'


class UserMe(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    active_org_id: UUID | None = None
    is_active: bool
    created_at: datetime


class InviteAcceptRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    token: str = Field(min_length=16, max_length=512)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

