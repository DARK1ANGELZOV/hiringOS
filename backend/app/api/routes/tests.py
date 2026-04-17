from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_candidate_use_cases, get_current_user, get_test_service
from app.api.serializers import (
    knowledge_test_answer_to_schema,
    knowledge_test_attempt_to_schema,
    knowledge_test_detail_to_schema,
    knowledge_test_question_to_schema,
    knowledge_test_to_schema,
    question_bank_to_schema,
)
from app.core.database import get_db
from app.models.enums import InterviewStage, UserRole
from app.models.user import User
from app.schemas.tests import (
    InterviewQuestionBankCreateRequest,
    InterviewQuestionBankResponse,
    KnowledgeTestAnswerResponse,
    KnowledgeTestAnswerSubmitRequest,
    KnowledgeTestAttemptResponse,
    KnowledgeTestAttemptStartRequest,
    KnowledgeTestCreateRequest,
    KnowledgeTestDetailResponse,
    KnowledgeTestFinishResponse,
    KnowledgeTestGenerateRequest,
    KnowledgeTestListResponse,
    KnowledgeTestResponse,
)
from app.services.test_service import KnowledgeTestService
from app.use_cases.candidates.use_cases import CandidateUseCases

router = APIRouter(prefix='/tests', tags=['tests'])


@router.post('', response_model=KnowledgeTestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_test(
    payload: KnowledgeTestCreateRequest,
    service: KnowledgeTestService = Depends(get_test_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await service.create_custom_test(
        payload=payload,
        creator_user_id=current_user.id,
        creator_role=current_user.role,
    )
    await db.commit()
    return knowledge_test_detail_to_schema(item)


@router.post('/generate', response_model=KnowledgeTestDetailResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_test(
    payload: KnowledgeTestGenerateRequest,
    service: KnowledgeTestService = Depends(get_test_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await service.generate_test(
        payload=payload,
        creator_user_id=current_user.id,
        creator_role=current_user.role,
    )
    await db.commit()
    return knowledge_test_detail_to_schema(item)


@router.get('', response_model=KnowledgeTestListResponse)
async def list_tests(
    topic: str | None = Query(default=None),
    subtype: str | None = Query(default=None),
    my_only: bool = Query(default=False),
    service: KnowledgeTestService = Depends(get_test_service),
    current_user: User = Depends(get_current_user),
):
    creator_filter = current_user.id if my_only else None
    items = await service.list_tests(topic=topic, subtype=subtype, created_by_user_id=creator_filter)

    if current_user.role == UserRole.CANDIDATE:
        items = [item for item in items if item.is_active]

    return KnowledgeTestListResponse(items=[knowledge_test_to_schema(item) for item in items])


@router.get('/{test_id}', response_model=KnowledgeTestDetailResponse)
async def get_test(
    test_id: UUID,
    service: KnowledgeTestService = Depends(get_test_service),
    current_user: User = Depends(get_current_user),
):
    item = await service.get_test(test_id)
    _ = current_user
    return knowledge_test_detail_to_schema(item)


@router.post('/{test_id}/start', response_model=KnowledgeTestAttemptResponse, status_code=status.HTTP_201_CREATED)
async def start_attempt(
    test_id: UUID,
    payload: KnowledgeTestAttemptStartRequest,
    service: KnowledgeTestService = Depends(get_test_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.CANDIDATE:
        candidate = await candidate_use_cases.get_by_owner(UUID(str(current_user.id)))
        candidate_id = candidate.id
    else:
        if not payload.session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='session_id is required for non-candidate start')
        session = await service.interview_repository.get_session(payload.session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interview session not found')
        candidate_id = session.candidate_id

    attempt = await service.start_attempt(test_id=test_id, candidate_id=candidate_id, session_id=payload.session_id)
    await db.commit()
    return knowledge_test_attempt_to_schema(attempt)


@router.post('/attempts/{attempt_id}/answer', response_model=KnowledgeTestAnswerResponse)
async def submit_test_answer(
    attempt_id: UUID,
    payload: KnowledgeTestAnswerSubmitRequest,
    service: KnowledgeTestService = Depends(get_test_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    item = await service.submit_answer(attempt_id=attempt_id, payload=payload)
    await db.commit()
    return knowledge_test_answer_to_schema(item)


@router.post('/attempts/{attempt_id}/finish', response_model=KnowledgeTestFinishResponse)
async def finish_test_attempt(
    attempt_id: UUID,
    service: KnowledgeTestService = Depends(get_test_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    attempt = await service.finish_attempt(attempt_id=attempt_id)
    questions = await service.repository.list_questions(attempt.test_id)
    answered_count = await service.repository.count_answers(attempt.id)
    await db.commit()
    return KnowledgeTestFinishResponse(
        attempt=knowledge_test_attempt_to_schema(attempt),
        answered_count=answered_count,
        total_questions=len(questions),
    )


@router.get('/attempts/list', response_model=list[KnowledgeTestAttemptResponse])
async def list_attempts(
    test_id: UUID | None = Query(default=None),
    candidate_id: UUID | None = Query(default=None),
    service: KnowledgeTestService = Depends(get_test_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.CANDIDATE:
        candidate = await candidate_use_cases.get_by_owner(UUID(str(current_user.id)))
        candidate_id = candidate.id

    items = await service.list_attempts(test_id=test_id, candidate_id=candidate_id)
    return [knowledge_test_attempt_to_schema(item) for item in items]


@router.post('/question-bank', response_model=InterviewQuestionBankResponse, status_code=status.HTTP_201_CREATED)
async def create_question_bank_item(
    payload: InterviewQuestionBankCreateRequest,
    service: KnowledgeTestService = Depends(get_test_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await service.create_question_bank_item(
        payload=payload,
        creator_user_id=current_user.id,
        creator_role=current_user.role,
    )
    await db.commit()
    return question_bank_to_schema(item)


@router.get('/question-bank', response_model=list[InterviewQuestionBankResponse])
async def list_question_bank_items(
    vacancy_id: UUID | None = Query(default=None),
    stage: str | None = Query(default=None),
    mine: bool = Query(default=False),
    service: KnowledgeTestService = Depends(get_test_service),
    current_user: User = Depends(get_current_user),
):
    if stage:
        try:
            stage_enum = InterviewStage(stage)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid stage filter') from exc
    else:
        stage_enum = None
    creator_id = current_user.id if mine else None
    items = await service.list_question_bank(vacancy_id=vacancy_id, stage=stage_enum, creator_id=creator_id)
    return [question_bank_to_schema(item) for item in items]
