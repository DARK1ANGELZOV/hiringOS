import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.enums import UserRole
from app.models.organization import ManagerCandidateAccess, Organization, OrganizationInvite, OrganizationMembership
from app.repositories.base import BaseRepository

settings = get_settings()


class OrganizationRepository(BaseRepository[Organization]):
    async def count_organizations(self) -> int:
        value = await self.db.scalar(select(func.count(Organization.id)))
        return int(value or 0)

    async def owner_exists(self) -> bool:
        value = await self.db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.is_owner.is_(True),
                OrganizationMembership.is_active.is_(True),
            )
        )
        return int(value or 0) > 0

    async def create_organization(self, *, name: str, slug: str, created_by_user_id: UUID | None, is_bootstrap: bool) -> Organization:
        org = Organization(name=name, slug=slug, created_by_user_id=created_by_user_id, is_bootstrap=is_bootstrap)
        self.db.add(org)
        await self.db.flush()
        return org

    async def get_organization(self, organization_id: UUID) -> Organization | None:
        result = await self.db.execute(select(Organization).where(Organization.id == organization_id))
        return result.scalar_one_or_none()

    async def create_membership(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        role: UserRole,
        is_owner: bool = False,
        is_active: bool = True,
        metadata_json: dict | None = None,
    ) -> OrganizationMembership:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            is_owner=is_owner,
            is_active=is_active,
            metadata_json=metadata_json or {},
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def get_membership(self, *, organization_id: UUID, user_id: UUID, role: UserRole | None = None) -> OrganizationMembership | None:
        query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active.is_(True),
        )
        if role is not None:
            query = query.where(OrganizationMembership.role == role)
        result = await self.db.execute(query.order_by(OrganizationMembership.created_at.desc()))
        return result.scalars().first()

    async def get_default_membership_for_user(self, *, user_id: UUID) -> OrganizationMembership | None:
        priority = {
            UserRole.ADMIN: 0,
            UserRole.HR: 1,
            UserRole.MANAGER: 2,
            UserRole.CANDIDATE: 3,
        }
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active.is_(True),
            )
        )
        items = list(result.scalars().all())
        if not items:
            return None
        items.sort(key=lambda item: (priority.get(item.role, 99), not item.is_owner, item.created_at))
        return items[0]

    async def list_members(self, *, organization_id: UUID) -> list[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .order_by(OrganizationMembership.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_user_memberships(self, *, user_id: UUID) -> list[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
            .order_by(OrganizationMembership.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_membership_by_id(self, membership_id: UUID) -> OrganizationMembership | None:
        result = await self.db.execute(select(OrganizationMembership).where(OrganizationMembership.id == membership_id))
        return result.scalar_one_or_none()

    async def set_membership_active(self, *, membership_id: UUID, is_active: bool) -> OrganizationMembership | None:
        item = await self.get_membership_by_id(membership_id)
        if not item:
            return None
        item.is_active = is_active
        await self.db.flush()
        return item

    async def update_membership_role(self, *, membership_id: UUID, role: UserRole) -> OrganizationMembership | None:
        item = await self.get_membership_by_id(membership_id)
        if not item:
            return None
        item.role = role
        await self.db.flush()
        return item

    async def grant_manager_candidate_access(
        self,
        *,
        organization_id: UUID,
        manager_user_id: UUID,
        candidate_id: UUID,
        granted_by_user_id: UUID | None,
    ) -> ManagerCandidateAccess:
        result = await self.db.execute(
            select(ManagerCandidateAccess).where(
                ManagerCandidateAccess.organization_id == organization_id,
                ManagerCandidateAccess.manager_user_id == manager_user_id,
                ManagerCandidateAccess.candidate_id == candidate_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_active = True
            existing.granted_by_user_id = granted_by_user_id
            await self.db.flush()
            return existing
        row = ManagerCandidateAccess(
            organization_id=organization_id,
            manager_user_id=manager_user_id,
            candidate_id=candidate_id,
            granted_by_user_id=granted_by_user_id,
            is_active=True,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def has_manager_candidate_access(self, *, organization_id: UUID, manager_user_id: UUID, candidate_id: UUID) -> bool:
        value = await self.db.scalar(
            select(func.count(ManagerCandidateAccess.id)).where(
                ManagerCandidateAccess.organization_id == organization_id,
                ManagerCandidateAccess.manager_user_id == manager_user_id,
                ManagerCandidateAccess.candidate_id == candidate_id,
                ManagerCandidateAccess.is_active.is_(True),
            )
        )
        return int(value or 0) > 0

    async def create_invite(
        self,
        *,
        organization_id: UUID,
        role: UserRole,
        email: str,
        created_by: UUID | None,
        metadata_json: dict | None = None,
    ) -> tuple[OrganizationInvite, str]:
        token = secrets.token_urlsafe(42)
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        invite = OrganizationInvite(
            organization_id=organization_id,
            role=role,
            email=email.lower().strip(),
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.invite_expires_hours),
            created_by=created_by,
            metadata_json=metadata_json or {},
        )
        self.db.add(invite)
        await self.db.flush()
        return invite, token

    async def get_invite_by_token(self, token: str) -> OrganizationInvite | None:
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        result = await self.db.execute(select(OrganizationInvite).where(OrganizationInvite.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def mark_invite_used(self, *, invite_id: UUID, used_by_user_id: UUID) -> OrganizationInvite | None:
        result = await self.db.execute(select(OrganizationInvite).where(OrganizationInvite.id == invite_id))
        invite = result.scalar_one_or_none()
        if not invite:
            return None
        invite.used_at = datetime.now(timezone.utc)
        invite.used_by_user_id = used_by_user_id
        await self.db.flush()
        return invite

    async def list_invites(self, *, organization_id: UUID, email: str | None = None) -> list[OrganizationInvite]:
        query = select(OrganizationInvite).where(OrganizationInvite.organization_id == organization_id)
        if email:
            query = query.where(OrganizationInvite.email == email.lower().strip())
        result = await self.db.execute(query.order_by(OrganizationInvite.created_at.desc()))
        return list(result.scalars().all())

    async def is_manager_allowed_candidate(self, *, organization_id: UUID, manager_user_id: UUID, candidate_id: UUID) -> bool:
        if await self.has_manager_candidate_access(
            organization_id=organization_id,
            manager_user_id=manager_user_id,
            candidate_id=candidate_id,
        ):
            return True
        # Managers are also allowed if they are interviewer in sessions with this candidate.
        # Kept intentionally in repository layer for deterministic scope checks.
        return False
