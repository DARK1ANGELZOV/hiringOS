from typing import Iterable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.api.serializers import vacancy_application_to_schema, vacancy_candidate_view_to_schema
from app.core.database import get_db
from app.models.enums import UserRole, VacancyApplicationStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.vacancy_application_repository import VacancyApplicationRepository
from app.repositories.vacancy_repository import VacancyRepository
from app.schemas.vacancy import (
    VacancyApplicationResponse,
    VacancyApplicationStatusUpdateRequest,
    VacancyApplyRequest,
    VacancyCandidateViewResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix='/vacancies', tags=['vacancies'])


def _tokenize_values(values: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        raw = (value or '').strip().lower()
        if not raw:
            continue
        for separator in [',', ';', '\n', '/', '|']:
            raw = raw.replace(separator, ' ')
        tokens.update(item.strip() for item in raw.split(' ') if item.strip())
    return tokens


def _candidate_skill_tokens(candidate) -> set[str]:
    values: list[str] = []
    if candidate.skills_raw:
        values.append(candidate.skills_raw)
    if candidate.competencies_raw:
        values.append(candidate.competencies_raw)
    for item in candidate.skills or []:
        if isinstance(item, dict):
            name = item.get('name')
            if isinstance(name, str):
                values.append(name)
        elif isinstance(item, str):
            values.append(item)
    return _tokenize_values(values)


def _vacancy_stack_tokens(vacancy) -> set[str]:
    values = [item for item in (vacancy.stack_json or []) if isinstance(item, str)]
    return _tokenize_values(values)


def _build_match(vacancy, candidate) -> dict:
    candidate_tokens = _candidate_skill_tokens(candidate)
    vacancy_tokens = _vacancy_stack_tokens(vacancy)
    if not vacancy_tokens:
        return {'score_percent': 0.0, 'matched_skills': [], 'missing_skills': []}

    matched = sorted(vacancy_tokens.intersection(candidate_tokens))
    missing = sorted(vacancy_tokens.difference(candidate_tokens))
    score = round((len(matched) / max(1, len(vacancy_tokens))) * 100.0, 2)
    return {'score_percent': score, 'matched_skills': matched, 'missing_skills': missing}


async def _assert_candidate_scope(candidate, *, current_user: User, candidate_repository: CandidateRepository) -> None:
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.ADMIN:
        return
    if active_role == UserRole.CANDIDATE:
        if candidate.owner_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
        return
    if active_role == UserRole.HR:
        if candidate.organization_id != getattr(current_user, 'active_org_id', None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        return
    if active_role == UserRole.MANAGER:
        active_org_id = getattr(current_user, 'active_org_id', None)
        if candidate.organization_id != active_org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        has_access = await candidate_repository.manager_has_access(
            manager_user_id=current_user.id,
            organization_id=active_org_id,
            candidate_id=candidate.id,
        )
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager candidate scope denied')
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')


@router.get('', response_model=list[VacancyCandidateViewResponse])
async def list_vacancies(
    limit: int = Query(default=200, ge=1, le=500),
    candidate_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vacancy_repository = VacancyRepository(db)
    candidate_repository = CandidateRepository(db)
    vacancies = await vacancy_repository.list(limit=limit)

    candidate = None
    if candidate_id is not None:
        candidate = await candidate_repository.get_by_id(candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')
        await _assert_candidate_scope(candidate, current_user=current_user, candidate_repository=candidate_repository)

    payload: list[VacancyCandidateViewResponse] = []
    for vacancy in vacancies:
        match = _build_match(vacancy, candidate) if candidate is not None else None
        payload.append(vacancy_candidate_view_to_schema(vacancy, match=match))
    return payload


@router.post(
    '/{vacancy_id:uuid}/apply',
    response_model=VacancyApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_vacancy(
    vacancy_id: UUID,
    payload: VacancyApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
):
    candidate_repository = CandidateRepository(db)
    vacancy_repository = VacancyRepository(db)
    application_repository = VacancyApplicationRepository(db)
    audit_service = AuditService(AuditRepository(db))

    candidate = await candidate_repository.get_by_owner_user_id(UUID(str(current_user.id)))
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Candidate profile is required')

    vacancy = await vacancy_repository.get_by_id(vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vacancy not found')

    existing = await application_repository.get_by_vacancy_and_candidate(vacancy_id=vacancy_id, candidate_id=candidate.id)
    if existing and existing.status != VacancyApplicationStatus.WITHDRAWN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Application already exists')

    if existing and existing.status == VacancyApplicationStatus.WITHDRAWN:
        updated = await application_repository.update_status(
            item=existing,
            status=VacancyApplicationStatus.APPLIED,
            note=payload.note,
        )
        updated.cover_letter_text = payload.cover_letter_text
        updated.metadata_json = payload.metadata_json
        await db.flush()
        application = updated
    else:
        application = await application_repository.create(
            vacancy_id=vacancy_id,
            candidate_id=candidate.id,
            created_by_user_id=current_user.id,
            cover_letter_text=payload.cover_letter_text,
            note=payload.note,
            metadata_json=payload.metadata_json,
        )

    await audit_service.log(
        action='vacancy.apply',
        user_id=UUID(str(current_user.id)),
        entity_type='vacancy_application',
        entity_id=str(application.id),
        metadata_json={'vacancy_id': str(vacancy_id), 'candidate_id': str(candidate.id)},
    )
    await db.commit()
    return vacancy_application_to_schema(application)


@router.get('/my-applications', response_model=list[VacancyApplicationResponse])
async def list_my_applications(
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
):
    candidate_repository = CandidateRepository(db)
    candidate = await candidate_repository.get_by_owner_user_id(UUID(str(current_user.id)))
    if not candidate:
        return []
    rows = await VacancyApplicationRepository(db).list(candidate_id=candidate.id, limit=limit)
    return [vacancy_application_to_schema(item) for item in rows]


@router.get('/applications', response_model=list[VacancyApplicationResponse])
async def list_applications(
    limit: int = Query(default=200, ge=1, le=500),
    vacancy_id: UUID | None = Query(default=None),
    candidate_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias='status'),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate_repository = CandidateRepository(db)
    active_role = getattr(current_user, 'active_role', current_user.role)
    parsed_status = None
    if status_filter:
        try:
            parsed_status = VacancyApplicationStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid status') from exc

    if active_role == UserRole.CANDIDATE:
        candidate = await candidate_repository.get_by_owner_user_id(UUID(str(current_user.id)))
        if not candidate:
            return []
        rows = await VacancyApplicationRepository(db).list(
            candidate_id=candidate.id,
            vacancy_id=vacancy_id,
            status=parsed_status,
            limit=limit,
        )
        return [vacancy_application_to_schema(item) for item in rows]

    if active_role not in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')

    rows = await VacancyApplicationRepository(db).list(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        status=parsed_status,
        limit=limit,
    )

    if active_role == UserRole.ADMIN:
        return [vacancy_application_to_schema(item) for item in rows]

    visible: list = []
    for item in rows:
        candidate = await candidate_repository.get_by_id(item.candidate_id)
        if not candidate:
            continue
        try:
            await _assert_candidate_scope(candidate, current_user=current_user, candidate_repository=candidate_repository)
            visible.append(item)
        except HTTPException:
            continue
    return [vacancy_application_to_schema(item) for item in visible]


@router.patch('/applications/{application_id:uuid}/status', response_model=VacancyApplicationResponse)
async def update_application_status(
    application_id: UUID,
    payload: VacancyApplicationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application_repository = VacancyApplicationRepository(db)
    candidate_repository = CandidateRepository(db)
    audit_service = AuditService(AuditRepository(db))

    item = await application_repository.get_by_id(application_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Application not found')

    try:
        new_status = VacancyApplicationStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid status') from exc

    active_role = getattr(current_user, 'active_role', current_user.role)
    candidate = await candidate_repository.get_by_id(item.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')

    if active_role == UserRole.CANDIDATE:
        if candidate.owner_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
        if new_status != VacancyApplicationStatus.WITHDRAWN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidates can only withdraw applications')
    elif active_role in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
        await _assert_candidate_scope(candidate, current_user=current_user, candidate_repository=candidate_repository)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')

    updated = await application_repository.update_status(item=item, status=new_status, note=payload.note)
    await audit_service.log(
        action='vacancy.application.status_change',
        user_id=UUID(str(current_user.id)),
        entity_type='vacancy_application',
        entity_id=str(updated.id),
        metadata_json={'status': new_status.value},
    )
    await db.commit()
    return vacancy_application_to_schema(updated)
