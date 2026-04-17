from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    ManagerCandidateAccessRequest,
    OrganizationCreateRequest,
    OrganizationInviteCreateRequest,
    OrganizationInviteResponse,
    OrganizationMembershipResponse,
    OrganizationResponse,
)
from app.services.audit_service import AuditService
from app.services.organization_service import OrganizationService

router = APIRouter(prefix='/organizations', tags=['organizations'])


def _organization_schema(item) -> OrganizationResponse:
    return OrganizationResponse(
        id=item.id,
        name=item.name,
        slug=item.slug,
        created_by_user_id=item.created_by_user_id,
        is_bootstrap=item.is_bootstrap,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _membership_schema(item) -> OrganizationMembershipResponse:
    return OrganizationMembershipResponse(
        id=item.id,
        organization_id=item.organization_id,
        user_id=item.user_id,
        role=item.role,
        is_owner=item.is_owner,
        is_active=item.is_active,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post('', response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    organization_repository = OrganizationRepository(db)
    current_org_id = getattr(current_user, 'active_org_id', None)
    if current_org_id:
        owner_membership = await organization_repository.get_membership(
            organization_id=current_org_id,
            user_id=current_user.id,
            role=UserRole.ADMIN,
        )
        if not owner_membership or not owner_membership.is_owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only organization owner can create organizations')

    service = OrganizationService(organization_repository)
    organization = await service.create_organization(
        creator_user_id=current_user.id,
        name=payload.name,
        slug=payload.slug,
    )

    await AuditService(AuditRepository(db)).log(
        action='organization.create',
        user_id=current_user.id,
        entity_type='organization',
        entity_id=str(organization.id),
        metadata_json={'name': organization.name, 'slug': organization.slug},
    )
    await db.commit()
    return _organization_schema(organization)


@router.post('/{organization_id}/invites', response_model=OrganizationInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    organization_id: UUID,
    payload: OrganizationInviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    organization_repository = OrganizationRepository(db)
    membership = await organization_repository.get_membership(
        organization_id=organization_id,
        user_id=current_user.id,
        role=UserRole.ADMIN,
    )
    if not membership or not membership.is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only organization owner can invite users')

    service = OrganizationService(organization_repository)
    invite, raw_token = await service.create_invite(
        organization_id=organization_id,
        role=payload.role,
        email=payload.email,
        created_by=current_user.id,
        metadata_json=payload.metadata_json,
    )

    await AuditService(AuditRepository(db)).log(
        action='organization.invite.create',
        user_id=current_user.id,
        entity_type='organization_invite',
        entity_id=str(invite.id),
        metadata_json={'organization_id': str(organization_id), 'role': payload.role.value, 'email': payload.email},
    )
    await db.commit()
    return OrganizationInviteResponse(
        id=invite.id,
        organization_id=invite.organization_id,
        role=invite.role,
        email=invite.email,
        expires_at=invite.expires_at,
        used_at=invite.used_at,
        created_by=invite.created_by,
        used_by_user_id=invite.used_by_user_id,
        created_at=invite.created_at,
        token=raw_token,
    )


@router.get('/{organization_id}/members', response_model=list[OrganizationMembershipResponse])
async def list_members(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.ADMIN, UserRole.HR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    organization_repository = OrganizationRepository(db)
    viewer_membership = await organization_repository.get_membership(
        organization_id=organization_id,
        user_id=current_user.id,
        role=active_role,
    )
    if not viewer_membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')

    members = await organization_repository.list_members(organization_id=organization_id)
    return [_membership_schema(item) for item in members]


@router.post('/{organization_id}/manager-access', response_model=OrganizationMembershipResponse)
async def grant_manager_candidate_access(
    organization_id: UUID,
    payload: ManagerCandidateAccessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.ADMIN, UserRole.HR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Permission denied')

    organization_repository = OrganizationRepository(db)
    viewer_membership = await organization_repository.get_membership(
        organization_id=organization_id,
        user_id=current_user.id,
        role=active_role,
    )
    if not viewer_membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')

    await organization_repository.grant_manager_candidate_access(
        organization_id=organization_id,
        manager_user_id=payload.manager_user_id,
        candidate_id=payload.candidate_id,
        granted_by_user_id=current_user.id,
    )
    await AuditService(AuditRepository(db)).log(
        action='organization.manager_candidate_access.grant',
        user_id=current_user.id,
        entity_type='candidate',
        entity_id=str(payload.candidate_id),
        metadata_json={'organization_id': str(organization_id), 'manager_user_id': str(payload.manager_user_id)},
    )
    await db.commit()
    # Return membership snapshot for manager as confirmation.
    membership = await organization_repository.get_membership(
        organization_id=organization_id,
        user_id=payload.manager_user_id,
        role=UserRole.MANAGER,
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Manager membership not found')
    return _membership_schema(membership)
