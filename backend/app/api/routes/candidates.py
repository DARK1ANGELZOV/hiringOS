from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_candidate_use_cases, get_current_user, require_roles
from app.api.serializers import candidate_status_history_to_schema, candidate_to_schema, profile_option_to_schema
from app.core.database import get_db
from app.models.enums import ProfileOptionType, UserRole
from app.models.user import User
from app.repositories.profile_option_repository import ProfileOptionRepository
from app.schemas.candidate import (
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateSearchRequest,
    CandidateSearchResponse,
    CandidateSearchResult,
    CandidateStatusHistoryResponse,
    CandidateStatusUpdateRequest,
    CandidateUpdate,
)
from app.schemas.profile_option import ProfileOptionCreateRequest, ProfileOptionResponse
from app.services.sanitizer import sanitize_text
from app.use_cases.candidates.use_cases import CandidateUseCases

router = APIRouter(prefix='/candidates', tags=['candidates'])


async def _assert_candidate_access(candidate, current_user: User, use_cases: CandidateUseCases) -> None:
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE and candidate.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')

    if active_role == UserRole.HR:
        if candidate.organization_id != getattr(current_user, 'active_org_id', None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')

    if active_role == UserRole.MANAGER:
        org_id = getattr(current_user, 'active_org_id', None)
        if candidate.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        has_access = await use_cases.candidate_service.repository.manager_has_access(
            manager_user_id=current_user.id,
            organization_id=org_id,
            candidate_id=candidate.id,
        )
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager candidate scope denied')


@router.post('', response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    payload: CandidateCreate,
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CANDIDATE, UserRole.HR, UserRole.MANAGER, UserRole.ADMIN)),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        existing = await use_cases.candidate_service.repository.get_by_owner_user_id(UUID(str(current_user.id)))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Candidate profile already exists')
        payload.organization_id = payload.organization_id or getattr(current_user, 'active_org_id', None)
        payload.owner_user_id = UUID(str(current_user.id))

    if active_role in {UserRole.HR, UserRole.MANAGER} and getattr(current_user, 'active_org_id', None) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
    if payload.organization_id is None:
        payload.organization_id = getattr(current_user, 'active_org_id', None)
    candidate = await use_cases.create(payload, actor_user_id=UUID(str(current_user.id)))
    await db.commit()
    fresh = await use_cases.get(candidate.id)
    return candidate_to_schema(fresh)


@router.get('', response_model=CandidateListResponse)
async def list_candidates(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    owner_user_id = UUID(str(current_user.id)) if active_role == UserRole.CANDIDATE else None
    active_org_id = getattr(current_user, 'active_org_id', None)
    manager_user_id = UUID(str(current_user.id)) if active_role == UserRole.MANAGER else None
    if active_role in {UserRole.HR, UserRole.MANAGER} and active_org_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
    items, total = await use_cases.list(
        status=status,
        limit=limit,
        offset=offset,
        owner_user_id=owner_user_id,
        organization_id=active_org_id if active_role in {UserRole.HR, UserRole.MANAGER} else None,
        manager_user_id=manager_user_id,
    )
    return CandidateListResponse(items=[candidate_to_schema(candidate) for candidate in items], total=total)


@router.post('/search', response_model=CandidateSearchResponse)
async def semantic_search(
    payload: CandidateSearchRequest,
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(require_roles(UserRole.HR, UserRole.MANAGER, UserRole.ADMIN)),
):
    _ = current_user
    results = await use_cases.search(query=payload.query, limit=payload.limit)
    return CandidateSearchResponse(
        items=[
            CandidateSearchResult(candidate=candidate_to_schema(candidate), score=score)
            for candidate, score in results
        ]
    )


@router.get('/{candidate_id:uuid}', response_model=CandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    candidate = await use_cases.get(candidate_id)
    await _assert_candidate_access(candidate, current_user, use_cases)
    return candidate_to_schema(candidate)


@router.patch('/{candidate_id:uuid}', response_model=CandidateResponse)
async def update_candidate(
    candidate_id: UUID,
    payload: CandidateUpdate,
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    candidate = await use_cases.get(candidate_id)
    await _assert_candidate_access(candidate, current_user, use_cases)

    if active_role == UserRole.CANDIDATE:
        payload.status = None
        payload.status_comment = None

    updated = await use_cases.update(candidate_id, payload, actor_user_id=UUID(str(current_user.id)))
    await db.commit()
    return candidate_to_schema(updated)


@router.patch('/{candidate_id:uuid}/status', response_model=CandidateResponse)
async def update_candidate_status(
    candidate_id: UUID,
    payload: CandidateStatusUpdateRequest,
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')

    candidate = await use_cases.get(candidate_id)
    await _assert_candidate_access(candidate, current_user, use_cases)

    updated = await use_cases.change_status(
        candidate_id=candidate_id,
        new_status=payload.new_status,
        actor_user_id=UUID(str(current_user.id)),
        comment=payload.comment,
        metadata_json=payload.metadata_json,
    )
    await db.commit()
    return candidate_to_schema(updated)


@router.get('/{candidate_id:uuid}/status-history', response_model=list[CandidateStatusHistoryResponse])
async def get_candidate_status_history(
    candidate_id: UUID,
    limit: int = Query(default=200, ge=1, le=500),
    use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    candidate = await use_cases.get(candidate_id)
    await _assert_candidate_access(candidate, current_user, use_cases)
    items = await use_cases.status_history(candidate_id=candidate_id, limit=limit)
    return [candidate_status_history_to_schema(item) for item in items]


@router.get('/profile-options/programming-languages', response_model=list[ProfileOptionResponse])
async def list_programming_language_options(
    limit: int = Query(default=500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    repository = ProfileOptionRepository(db)
    rows = await repository.list_by_type(option_type=ProfileOptionType.PROGRAMMING_LANGUAGE, limit=limit)
    return [profile_option_to_schema(row) for row in rows]


@router.post(
    '/profile-options/programming-languages',
    response_model=ProfileOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_programming_language_option(
    payload: ProfileOptionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = ProfileOptionRepository(db)
    normalized = sanitize_text(payload.value).strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Option value is empty')

    existing = await repository.get_by_type_and_normalized(
        option_type=ProfileOptionType.PROGRAMMING_LANGUAGE,
        normalized_value=normalized,
    )
    if existing:
        return profile_option_to_schema(existing)

    row = await repository.create(
        option_type=ProfileOptionType.PROGRAMMING_LANGUAGE,
        value=sanitize_text(payload.value).strip(),
        normalized_value=normalized,
        created_by_user_id=current_user.id,
    )
    await db.commit()
    return profile_option_to_schema(row)
