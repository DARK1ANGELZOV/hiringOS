import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.repositories.organization_repository import OrganizationRepository


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug[:100] or 'organization'


class OrganizationService:
    def __init__(self, repository: OrganizationRepository):
        self.repository = repository

    async def bootstrap_available(self) -> bool:
        if await self.repository.count_organizations() > 0:
            return False
        if await self.repository.owner_exists():
            return False
        return True

    async def create_bootstrap_for_user(self, *, user_id: UUID, user_full_name: str, user_email: str):
        if not await self.bootstrap_available():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Bootstrap already completed')

        base_name = f'{user_full_name} Organization'.strip()
        org = await self.repository.create_organization(
            name=base_name,
            slug=self._unique_slug(base_name, user_email),
            created_by_user_id=user_id,
            is_bootstrap=True,
        )
        await self.repository.create_membership(
            organization_id=org.id,
            user_id=user_id,
            role=UserRole.ADMIN,
            is_owner=True,
            is_active=True,
            metadata_json={'source': 'bootstrap'},
        )
        await self.repository.create_membership(
            organization_id=org.id,
            user_id=user_id,
            role=UserRole.HR,
            is_owner=True,
            is_active=True,
            metadata_json={'source': 'bootstrap'},
        )
        return org

    async def create_organization(self, *, creator_user_id: UUID, name: str, slug: str | None = None):
        final_slug = self._unique_slug(name, fallback=slug or name)
        org = await self.repository.create_organization(
            name=name.strip(),
            slug=final_slug,
            created_by_user_id=creator_user_id,
            is_bootstrap=False,
        )
        await self.repository.create_membership(
            organization_id=org.id,
            user_id=creator_user_id,
            role=UserRole.ADMIN,
            is_owner=True,
            is_active=True,
            metadata_json={'source': 'organization_create'},
        )
        return org

    async def create_invite(self, *, organization_id: UUID, role: UserRole, email: str, created_by: UUID | None, metadata_json: dict | None = None):
        if role not in {UserRole.HR, UserRole.MANAGER}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only HR and Manager invites are allowed')
        invite, raw_token = await self.repository.create_invite(
            organization_id=organization_id,
            role=role,
            email=email,
            created_by=created_by,
            metadata_json=metadata_json,
        )
        return invite, raw_token

    async def validate_invite_acceptance(self, *, token: str, email: str):
        invite = await self.repository.get_invite_by_token(token)
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invitation not found')

        if invite.used_at is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invitation already used')

        now = datetime.now(timezone.utc)
        expires_at = invite.expires_at if invite.expires_at.tzinfo else invite.expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Invitation expired')

        if invite.email.strip().lower() != email.strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invitation email mismatch')

        return invite

    async def assign_membership_from_invite(self, *, invite, user_id: UUID):
        membership = await self.repository.get_membership(
            organization_id=invite.organization_id,
            user_id=user_id,
            role=invite.role,
        )
        if membership:
            membership.is_active = True
            membership.metadata_json = {**(membership.metadata_json or {}), 'source': 'invite_accept'}
        else:
            membership = await self.repository.create_membership(
                organization_id=invite.organization_id,
                user_id=user_id,
                role=invite.role,
                is_owner=False,
                is_active=True,
                metadata_json={'source': 'invite_accept'},
            )
        await self.repository.mark_invite_used(invite_id=invite.id, used_by_user_id=user_id)
        return membership

    def _unique_slug(self, name: str, fallback: str) -> str:
        return _slugify(name or fallback)
