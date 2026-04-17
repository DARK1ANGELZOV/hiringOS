from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=128)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_by_user_id: UUID | None
    is_bootstrap: bool
    created_at: datetime
    updated_at: datetime


class OrganizationInviteCreateRequest(BaseModel):
    email: EmailStr
    role: UserRole
    metadata_json: dict = Field(default_factory=dict)


class OrganizationInviteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    role: UserRole
    email: EmailStr
    expires_at: datetime
    used_at: datetime | None
    created_by: UUID | None
    used_by_user_id: UUID | None
    created_at: datetime
    token: str | None = None


class OrganizationMembershipResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: UserRole
    is_owner: bool
    is_active: bool
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class ManagerCandidateAccessRequest(BaseModel):
    manager_user_id: UUID
    candidate_id: UUID

