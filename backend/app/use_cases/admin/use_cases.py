from uuid import UUID

from app.models.enums import UserRole
from app.services.admin_service import AdminService


class AdminUseCases:
    def __init__(self, *, admin_service: AdminService):
        self.admin_service = admin_service

    async def stats(self):
        return await self.admin_service.stats()

    async def audit_logs(self, limit: int = 200):
        return await self.admin_service.audit_logs(limit=limit)

    async def list_users(self, *, limit: int = 200, offset: int = 0):
        return await self.admin_service.list_users(limit=limit, offset=offset)

    async def block_user(self, *, user_id: UUID, reason: str | None = None):
        return await self.admin_service.block_user(user_id=user_id, reason=reason)

    async def unblock_user(self, *, user_id: UUID):
        return await self.admin_service.unblock_user(user_id=user_id)

    async def list_memberships(self, *, user_id: UUID):
        return await self.admin_service.list_memberships(user_id=user_id)

    async def assign_membership(self, *, organization_id: UUID, user_id: UUID, role: UserRole, is_owner: bool = False):
        return await self.admin_service.assign_membership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            is_owner=is_owner,
        )

    async def revoke_membership(self, *, membership_id: UUID):
        return await self.admin_service.revoke_membership(membership_id=membership_id)

    async def update_user_role(self, *, user_id: UUID, role: UserRole):
        return await self.admin_service.update_user_role(user_id=user_id, role=role)

    async def update_membership(self, *, membership_id: UUID, role: UserRole | None = None, is_active: bool | None = None):
        return await self.admin_service.update_membership(membership_id=membership_id, role=role, is_active=is_active)

    async def list_refresh_sessions(self, *, user_id: UUID, limit: int = 200):
        return await self.admin_service.list_refresh_sessions(user_id=user_id, limit=limit)

