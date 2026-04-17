from uuid import UUID

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.repositories.audit_repository import AdminRepository, AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AdminService:
    def __init__(
        self,
        *,
        admin_repository: AdminRepository,
        audit_repository: AuditRepository,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        refresh_repository: RefreshTokenRepository,
    ):
        self.admin_repository = admin_repository
        self.audit_repository = audit_repository
        self.user_repository = user_repository
        self.organization_repository = organization_repository
        self.refresh_repository = refresh_repository

    async def stats(self):
        return await self.admin_repository.stats()

    async def audit_logs(self, limit: int = 200):
        return await self.audit_repository.list_logs(limit=limit)

    async def list_users(self, *, limit: int = 200, offset: int = 0):
        return await self.user_repository.list_users(limit=limit, offset=offset)

    async def block_user(self, *, user_id: UUID, reason: str | None = None):
        user = await self.user_repository.set_active(user_id=user_id, is_active=False)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        await self.refresh_repository.revoke_all_for_user(user.id)
        await self.audit_repository.create(
            user_id=user.id,
            action='user.block',
            entity_type='user',
            entity_id=str(user.id),
            metadata_json={'reason': reason or ''},
        )
        return user

    async def unblock_user(self, *, user_id: UUID):
        user = await self.user_repository.set_active(user_id=user_id, is_active=True)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        await self.audit_repository.create(
            user_id=user.id,
            action='user.unblock',
            entity_type='user',
            entity_id=str(user.id),
            metadata_json={},
        )
        return user

    async def list_memberships(self, *, user_id: UUID):
        return await self.organization_repository.list_user_memberships(user_id=user_id)

    async def assign_membership(self, *, organization_id: UUID, user_id: UUID, role: UserRole, is_owner: bool = False):
        membership = await self.organization_repository.get_membership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        if membership:
            membership.is_active = True
            membership.is_owner = membership.is_owner or is_owner
            await self.organization_repository.db.flush()
        else:
            membership = await self.organization_repository.create_membership(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                is_owner=is_owner,
                is_active=True,
                metadata_json={'source': 'admin_assign'},
            )
        await self.audit_repository.create(
            user_id=user_id,
            action='membership.assign',
            entity_type='organization_membership',
            entity_id=str(membership.id),
            metadata_json={'organization_id': str(organization_id), 'role': role.value, 'is_owner': is_owner},
        )
        return membership

    async def revoke_membership(self, *, membership_id: UUID):
        membership = await self.organization_repository.set_membership_active(membership_id=membership_id, is_active=False)
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Membership not found')
        await self.audit_repository.create(
            user_id=membership.user_id,
            action='membership.revoke',
            entity_type='organization_membership',
            entity_id=str(membership.id),
            metadata_json={'organization_id': str(membership.organization_id), 'role': membership.role.value},
        )
        return membership

    async def update_user_role(self, *, user_id: UUID, role: UserRole):
        user = await self.user_repository.set_role(user_id=user_id, role=role.value)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        await self.audit_repository.create(
            user_id=user.id,
            action='user.role.change',
            entity_type='user',
            entity_id=str(user.id),
            metadata_json={'role': role.value},
        )
        return user

    async def update_membership(self, *, membership_id: UUID, role: UserRole | None = None, is_active: bool | None = None):
        membership = await self.organization_repository.get_membership_by_id(membership_id)
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Membership not found')

        if role is not None:
            membership = await self.organization_repository.update_membership_role(membership_id=membership_id, role=role)
            if not membership:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Membership not found')

        if is_active is not None:
            membership = await self.organization_repository.set_membership_active(membership_id=membership_id, is_active=is_active)
            if not membership:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Membership not found')

        await self.audit_repository.create(
            user_id=membership.user_id,
            action='membership.update',
            entity_type='organization_membership',
            entity_id=str(membership.id),
            metadata_json={
                'organization_id': str(membership.organization_id),
                'role': membership.role.value,
                'is_active': membership.is_active,
            },
        )
        return membership

    async def list_refresh_sessions(self, *, user_id: UUID, limit: int = 200):
        return await self.refresh_repository.list_user_sessions(user_id=user_id, limit=limit)
