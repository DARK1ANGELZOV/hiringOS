from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import UserRole


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    ip_address: str | None
    user_agent: str | None
    metadata: dict
    created_at: datetime


class AdminStatsResponse(BaseModel):
    users_total: int
    candidates_total: int
    interviews_total: int
    pending_notifications_total: int


class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserBlockRequest(BaseModel):
    reason: str | None = None


class MembershipRoleChangeRequest(BaseModel):
    role: UserRole


class AdminUserRoleChangeRequest(BaseModel):
    role: UserRole


class AdminMembershipAssignRequest(BaseModel):
    organization_id: UUID
    role: UserRole
    is_owner: bool = False


class AdminMembershipUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class RefreshSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    jti: str
    family_id: str
    session_id: str
    org_id: UUID | None
    role: str | None
    expires_at: datetime
    revoked_at: datetime | None
    revoked_reason: str | None
    reuse_detected_at: datetime | None
    created_at: datetime

