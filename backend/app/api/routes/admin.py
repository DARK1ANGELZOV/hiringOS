from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_use_cases, require_roles
from app.api.serializers import audit_to_schema, vacancy_to_schema
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.vacancy_repository import VacancyRepository
from app.schemas.admin import (
    AdminMembershipAssignRequest,
    AdminMembershipUpdateRequest,
    AdminStatsResponse,
    AdminUserResponse,
    AdminUserRoleChangeRequest,
    AuditLogResponse,
    RefreshSessionResponse,
    UserBlockRequest,
)
from app.schemas.organization import OrganizationMembershipResponse
from app.schemas.vacancy import VacancyCreateRequest, VacancyResponse
from app.services.audit_service import AuditService
from app.use_cases.admin.use_cases import AdminUseCases

router = APIRouter(prefix='/admin', tags=['admin'])


def _user_schema(user) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
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


@router.get('/stats', response_model=AdminStatsResponse)
async def stats(
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    data = await use_cases.stats()
    return AdminStatsResponse(**data)


@router.get('/audit-logs', response_model=list[AuditLogResponse])
async def audit_logs(
    limit: int = Query(default=200, ge=1, le=500),
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    logs = await use_cases.audit_logs(limit=limit)
    return [audit_to_schema(log) for log in logs]


@router.post('/vacancies', response_model=VacancyResponse, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    payload: VacancyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR, UserRole.MANAGER)),
):
    repository = VacancyRepository(db)
    vacancy = await repository.create(**payload.model_dump())

    await AuditService(AuditRepository(db)).log(
        action='vacancy.create',
        user_id=current_user.id,
        entity_type='vacancy',
        entity_id=str(vacancy.id),
        metadata_json={'title': vacancy.title, 'level': vacancy.level},
    )
    await db.commit()
    return vacancy_to_schema(vacancy)


@router.get('/vacancies', response_model=list[VacancyResponse])
async def list_vacancies(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.HR, UserRole.MANAGER, UserRole.CANDIDATE)),
):
    _ = current_user
    items = await VacancyRepository(db).list(limit=limit)
    return [vacancy_to_schema(item) for item in items]


@router.get('/users', response_model=list[AdminUserResponse])
async def list_users(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    users = await use_cases.list_users(limit=limit, offset=offset)
    return [_user_schema(user) for user in users]


@router.patch('/users/{user_id}/block', response_model=AdminUserResponse)
async def block_user(
    user_id: UUID,
    payload: UserBlockRequest,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    user = await use_cases.block_user(user_id=user_id, reason=payload.reason)
    await db.commit()
    return _user_schema(user)


@router.patch('/users/{user_id}/unblock', response_model=AdminUserResponse)
async def unblock_user(
    user_id: UUID,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    user = await use_cases.unblock_user(user_id=user_id)
    await db.commit()
    return _user_schema(user)


@router.patch('/users/{user_id}/role', response_model=AdminUserResponse)
async def update_user_role(
    user_id: UUID,
    payload: AdminUserRoleChangeRequest,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    user = await use_cases.update_user_role(user_id=user_id, role=payload.role)
    await db.commit()
    return _user_schema(user)


@router.get('/users/{user_id}/memberships', response_model=list[OrganizationMembershipResponse])
async def list_user_memberships(
    user_id: UUID,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    items = await use_cases.list_memberships(user_id=user_id)
    return [_membership_schema(item) for item in items]


@router.post('/users/{user_id}/memberships', response_model=OrganizationMembershipResponse, status_code=status.HTTP_201_CREATED)
async def assign_membership(
    user_id: UUID,
    payload: AdminMembershipAssignRequest,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    item = await use_cases.assign_membership(
        organization_id=payload.organization_id,
        user_id=user_id,
        role=payload.role,
        is_owner=payload.is_owner,
    )
    await db.commit()
    return _membership_schema(item)


@router.patch('/users/{user_id}/memberships/{membership_id}', response_model=OrganizationMembershipResponse)
async def update_membership(
    user_id: UUID,
    membership_id: UUID,
    payload: AdminMembershipUpdateRequest,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    item = await use_cases.update_membership(
        membership_id=membership_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    if item.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Membership does not belong to user')
    await db.commit()
    return _membership_schema(item)


@router.delete('/users/{user_id}/memberships/{membership_id}', response_model=OrganizationMembershipResponse)
async def revoke_membership(
    user_id: UUID,
    membership_id: UUID,
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    item = await use_cases.revoke_membership(membership_id=membership_id)
    if item.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Membership does not belong to user')
    await db.commit()
    return _membership_schema(item)


@router.get('/users/{user_id}/sessions', response_model=list[RefreshSessionResponse])
async def list_user_sessions(
    user_id: UUID,
    limit: int = Query(default=200, ge=1, le=500),
    use_cases: AdminUseCases = Depends(get_admin_use_cases),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    items = await use_cases.list_refresh_sessions(user_id=user_id, limit=limit)
    return [
        RefreshSessionResponse(
            id=item.id,
            user_id=item.user_id,
            jti=item.jti,
            family_id=item.family_id,
            session_id=item.session_id,
            org_id=item.org_id,
            role=item.role,
            expires_at=item.expires_at,
            revoked_at=item.revoked_at,
            revoked_reason=item.revoked_reason,
            reuse_detected_at=item.reuse_detected_at,
            created_at=item.created_at,
        )
        for item in items
    ]
