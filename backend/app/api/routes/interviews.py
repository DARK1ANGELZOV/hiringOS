from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_candidate_use_cases, get_current_user, get_interview_use_cases, require_roles
from app.api.serializers import (
    anti_cheat_signal_to_schema,
    ide_submission_to_schema,
    interview_event_to_schema,
    interview_question_to_schema,
    interview_request_to_schema,
    interview_to_schema,
    question_bank_to_schema,
)
from app.core.database import SessionLocal, get_db
from app.core.limiter import limiter
from app.core.security import decode_access_token
from app.models.enums import AnalysisStatus, InterviewStage, UserRole
from app.models.user import User
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interview import (
    InterviewLiveStateResponse,
    InterviewInviteDecisionRequest,
    IdeSubmissionRequest,
    IdeSubmissionResponse,
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewCreateRequest,
    InterviewEventIngestRequest,
    InterviewEventResponse,
    InterviewFinishResponse,
    InterviewProgress,
    InterviewQuestionsListResponse,
    InterviewRequestCreateRequest,
    InterviewRequestResponse,
    InterviewRequestReviewRequest,
    InterviewReportResponse,
    InterviewScheduleUpdateRequest,
    InterviewSpeechDiagnosticsResponse,
    InterviewSessionResponse,
    InterviewSignalsResponse,
    InterviewStartResponse,
    InterviewVideoFrameIngestRequest,
    InterviewVideoFrameIngestResponse,
)
from app.integrations.ai_service import ai_client
from app.schemas.tests import InterviewQuestionBankCreateRequest, InterviewQuestionBankResponse
from app.services.ws_manager import ws_manager
from app.use_cases.candidates.use_cases import CandidateUseCases
from app.use_cases.interviews.use_cases import InterviewUseCases

router = APIRouter(prefix='/interviews', tags=['interviews'])
ws_router = APIRouter(prefix='/ws/interviews', tags=['interviews-ws'])


async def _assert_session_access(
    *,
    session,
    current_user: User,
    candidate_use_cases: CandidateUseCases,
    allow_candidate: bool = True,
) -> UUID | None:
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        if not allow_candidate:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
        candidate = await candidate_use_cases.get_by_owner(UUID(str(current_user.id)))
        if session.candidate_id != candidate.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
        return candidate.id

    if active_role == UserRole.HR:
        candidate = await candidate_use_cases.get(session.candidate_id)
        if candidate.organization_id != getattr(current_user, 'active_org_id', None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')

    if active_role == UserRole.MANAGER:
        candidate = await candidate_use_cases.get(session.candidate_id)
        org_id = getattr(current_user, 'active_org_id', None)
        if candidate.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        has_access = await candidate_use_cases.candidate_service.repository.manager_has_access(
            manager_user_id=current_user.id,
            organization_id=org_id,
            candidate_id=candidate.id,
        )
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager candidate scope denied')
    return None


async def _build_progress(use_cases: InterviewUseCases, session_id: UUID):
    repository = use_cases.interview_service.repository
    answered = await repository.count_answers(session_id)
    question_total = await repository.count_questions(session_id)
    ide_tasks_total = len(await repository.list_ide_tasks(session_id))
    ide_submissions = len(await repository.list_ide_submissions(session_id))

    total = question_total + ide_tasks_total
    completed = answered + min(ide_submissions, ide_tasks_total)
    percent = round((completed / total) * 100.0, 2) if total else 0.0
    return InterviewProgress(answered=completed, total=total, stage=session.current_stage, progress_percent=percent)


async def _assert_ws_access(session_id: UUID, user_id: UUID) -> tuple[str, bool]:
    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User unavailable')

        session = await InterviewRepository(db).get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interview session not found')

        is_candidate_owner = False
        if user.role == UserRole.CANDIDATE:
            candidate = await CandidateRepository(db).get_by_owner_user_id(user.id)
            if not candidate or candidate.id != session.candidate_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidate access denied for this session')
            is_candidate_owner = True

        if user.role in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
            return user.role.value, False

        if is_candidate_owner:
            return user.role.value, True

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')


def _report_schema_from_assessment(assessment) -> InterviewReportResponse:
    if not assessment:
        return InterviewReportResponse(generation_status=AnalysisStatus.GENERATION_PENDING)

    return InterviewReportResponse(
        generation_status=assessment.generation_status,
        summary_text=assessment.summary_text,
        score_total=assessment.score_total,
        score_hard_skills=assessment.score_hard_skills,
        score_soft_skills=assessment.score_soft_skills,
        score_communication=assessment.score_communication,
        score_problem_solving=assessment.score_problem_solving,
        score_code_quality=assessment.score_code_quality,
        score_business_thinking=assessment.score_business_thinking,
        risk_flags_json=assessment.risk_flags_json,
        recommendations_json=assessment.recommendations_json,
        raw_result_json=assessment.raw_result_json,
    )


@router.post('', response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit('30/minute')
async def create_interview(
    request: Request,
    payload: InterviewCreateRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidates cannot create interviews')

    session = await use_cases.create_session(payload, actor_user_id=UUID(str(current_user.id)))
    await db.commit()
    return interview_to_schema(session)


@router.get('/{session_id:uuid}', response_model=InterviewSessionResponse)
async def get_interview(
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)
    return interview_to_schema(session)


@router.get('', response_model=list[InterviewSessionResponse])
async def list_interviews(
    candidate_id: UUID | None = Query(default=None),
    interviewer_id: UUID | None = Query(default=None),
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        candidate = await candidate_use_cases.get_by_owner(UUID(str(current_user.id)))
        candidate_id = candidate.id

    sessions = await use_cases.list_sessions(candidate_id=candidate_id, interviewer_id=interviewer_id)
    return [interview_to_schema(session) for session in sessions]


@router.post('/requests', response_model=InterviewRequestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit('40/minute')
async def create_interview_request(
    request: Request,
    payload: InterviewRequestCreateRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only manager/admin can request interviews')

    candidate = await candidate_use_cases.get(payload.candidate_id)
    org_id = getattr(current_user, 'active_org_id', None)
    if active_role == UserRole.MANAGER:
        if candidate.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        has_access = await candidate_use_cases.candidate_service.repository.manager_has_access(
            manager_user_id=current_user.id,
            organization_id=org_id,
            candidate_id=candidate.id,
        )
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager candidate scope denied')

    item = await use_cases.create_request(payload=payload, actor_user_id=UUID(str(current_user.id)))
    await db.commit()
    return interview_request_to_schema(item)


@router.get('/requests', response_model=list[InterviewRequestResponse])
async def list_interview_requests(
    status_filter: str | None = Query(default=None, alias='status'),
    candidate_id: UUID | None = Query(default=None),
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidates cannot list interview requests')
    manager_user_id = UUID(str(current_user.id)) if active_role == UserRole.MANAGER else None
    hr_user_id = UUID(str(current_user.id)) if active_role == UserRole.HR else None
    items = await use_cases.list_requests(
        manager_user_id=manager_user_id,
        hr_user_id=hr_user_id,
        candidate_id=candidate_id,
        status_filter=status_filter,
    )
    return [interview_request_to_schema(item) for item in items]


@router.get('/speech/diagnostics', response_model=InterviewSpeechDiagnosticsResponse)
async def speech_diagnostics(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE, UserRole.HR, UserRole.MANAGER, UserRole.ADMIN)),
):
    _ = current_user
    payload = await ai_client.speech_diagnostics()
    return InterviewSpeechDiagnosticsResponse(
        stt_loaded=bool(payload.get('stt_loaded', False)),
        stt_error=payload.get('stt_error'),
        tts_loaded=bool(payload.get('tts_loaded', False)),
        tts_error=payload.get('tts_error'),
    )


@router.patch('/requests/{request_id}/review', response_model=InterviewRequestResponse)
@limiter.limit('40/minute')
async def review_interview_request(
    request: Request,
    request_id: UUID,
    payload: InterviewRequestReviewRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.HR, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Admin can review interview requests')
    item, _session = await use_cases.review_request(request_id=request_id, payload=payload, actor_user_id=UUID(str(current_user.id)))
    await db.commit()
    return interview_request_to_schema(item)


@router.post('/{session_id:uuid}/start', response_model=InterviewStartResponse)
@limiter.limit('40/minute')
async def start_interview(
    request: Request,
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)

    session, first_question = await use_cases.start_session(session_id=session_id, actor_user_id=UUID(str(current_user.id)))
    progress = await _build_progress(use_cases, session.id)

    await ws_manager.broadcast(
        session.id,
        'stage_transition',
        {'status': session.status.value, 'stage': session.current_stage.value if session.current_stage else None},
    )
    if first_question:
        await ws_manager.broadcast(session.id, 'question_ready', interview_question_to_schema(first_question).model_dump(mode='json'))

    await db.commit()
    return InterviewStartResponse(
        session=interview_to_schema(session),
        first_question=interview_question_to_schema(first_question) if first_question else None,
        progress=progress,
    )


@router.patch('/{session_id:uuid}/schedule', response_model=InterviewSessionResponse)
@limiter.limit('40/minute')
async def update_interview_schedule(
    request: Request,
    session_id: UUID,
    payload: InterviewScheduleUpdateRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(
        session=session,
        current_user=current_user,
        candidate_use_cases=candidate_use_cases,
        allow_candidate=False,
    )
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.HR, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Admin can schedule interviews')
    updated = await use_cases.update_schedule(
        session_id=session_id,
        payload=payload,
        actor_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return interview_to_schema(updated)


@router.post('/{session_id:uuid}/invite/decision', response_model=InterviewSessionResponse)
@limiter.limit('120/minute')
async def submit_invite_decision(
    request: Request,
    session_id: UUID,
    payload: InterviewInviteDecisionRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(
        session=session,
        current_user=current_user,
        candidate_use_cases=candidate_use_cases,
        allow_candidate=True,
    )
    active_role = getattr(current_user, 'active_role', current_user.role)
    role = payload.role.strip().lower()
    if active_role == UserRole.CANDIDATE and role != 'candidate':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidate can update only candidate decision')
    if active_role == UserRole.MANAGER and role != 'manager':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager can update only manager decision')

    updated = await use_cases.set_invite_decision(
        session_id=session_id,
        payload=payload,
        actor_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return interview_to_schema(updated)


@router.post('/{session_id:uuid}/answer', response_model=InterviewAnswerResponse)
@limiter.limit('180/minute')
async def submit_answer(
    request: Request,
    session_id: UUID,
    payload: InterviewAnswerRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    candidate_id = await _assert_session_access(
        session=session,
        current_user=current_user,
        candidate_use_cases=candidate_use_cases,
        allow_candidate=True,
    )

    if candidate_id is None:
        candidate_id = session.candidate_id

    session, next_question, analysis_status = await use_cases.submit_answer(
        session_id=session_id,
        candidate_id=candidate_id,
        payload=payload,
        actor_user_id=UUID(str(current_user.id)),
    )

    progress = await _build_progress(use_cases, session.id)

    await ws_manager.broadcast(session.id, 'progress_update', progress.model_dump(mode='json'))
    await ws_manager.broadcast(
        session.id,
        'stage_transition',
        {'status': session.status.value, 'stage': session.current_stage.value if session.current_stage else None},
    )
    if next_question:
        await ws_manager.broadcast(session.id, 'question_ready', interview_question_to_schema(next_question).model_dump(mode='json'))

    await db.commit()
    return InterviewAnswerResponse(
        accepted=True,
        current_question_id=payload.question_id,
        next_question=interview_question_to_schema(next_question) if next_question else None,
        session_status=session.status,
        stage=session.current_stage,
        progress=progress,
        ai_analysis_status=analysis_status,
    )


@router.post('/{session_id:uuid}/finish', response_model=InterviewFinishResponse)
@limiter.limit('40/minute')
async def finish_interview(
    request: Request,
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)

    finished, task_id = await use_cases.finish_session(session_id=session_id, actor_user_id=UUID(str(current_user.id)))

    await ws_manager.broadcast(
        finished.id,
        'interview_finished',
        {
            'status': finished.status.value,
            'analysis_status': finished.analysis_status.value,
            'analysis_task_id': task_id,
        },
    )

    await db.commit()
    return InterviewFinishResponse(
        status=finished.status,
        analysis_status=finished.analysis_status,
        analysis_task_id=task_id,
    )


@router.get('/{session_id:uuid}/report', response_model=InterviewReportResponse)
async def get_interview_report(
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.CANDIDATE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Candidates cannot access report directly')

    _session, assessment = await use_cases.get_report(session_id)
    return _report_schema_from_assessment(assessment)


@router.get('/{session_id:uuid}/questions', response_model=InterviewQuestionsListResponse)
async def get_questions(
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)

    questions, current_question = await use_cases.list_questions(session_id)
    return InterviewQuestionsListResponse(
        items=[interview_question_to_schema(item) for item in questions],
        current_question_id=current_question.id if current_question else None,
    )


@router.post('/{session_id:uuid}/ide/submit', response_model=IdeSubmissionResponse)
@limiter.limit('80/minute')
async def submit_ide(
    request: Request,
    session_id: UUID,
    payload: IdeSubmissionRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    candidate_id = await _assert_session_access(
        session=session,
        current_user=current_user,
        candidate_use_cases=candidate_use_cases,
        allow_candidate=True,
    )

    if candidate_id is None:
        candidate_id = session.candidate_id

    submission = await use_cases.submit_ide(
        session_id=session_id,
        candidate_id=candidate_id,
        payload=payload,
        actor_user_id=UUID(str(current_user.id)),
    )

    await ws_manager.broadcast(
        session.id,
        'ide_task_submitted',
        ide_submission_to_schema(submission).model_dump(mode='json'),
    )

    await db.commit()
    return ide_submission_to_schema(submission)


@router.post('/{session_id:uuid}/events', response_model=InterviewEventResponse)
@limiter.limit('240/minute')
async def ingest_interview_event(
    request: Request,
    session_id: UUID,
    payload: InterviewEventIngestRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)

    event = await use_cases.ingest_event(
        session_id=session_id,
        event_type=payload.event_type,
        payload_json=payload.payload_json,
        actor_user_id=UUID(str(current_user.id)),
    )

    event_schema = interview_event_to_schema(event)
    await ws_manager.broadcast(session.id, 'event', event_schema.model_dump(mode='json'))

    await db.commit()
    return event_schema


@router.get('/{session_id:uuid}/signals', response_model=InterviewSignalsResponse)
async def get_signals(
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Manager/Admin can view anti-cheat signals')

    score, risk, signals = await use_cases.get_signals(session_id)
    return InterviewSignalsResponse(
        risk_level=risk,
        anti_cheat_score=score,
        items=[anti_cheat_signal_to_schema(item) for item in signals],
    )


@router.post('/{session_id:uuid}/video/frame', response_model=InterviewVideoFrameIngestResponse)
@limiter.limit('120/minute')
async def ingest_video_frame(
    request: Request,
    session_id: UUID,
    payload: InterviewVideoFrameIngestRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = request
    session = await use_cases.get_session(session_id)
    await _assert_session_access(
        session=session,
        current_user=current_user,
        candidate_use_cases=candidate_use_cases,
        allow_candidate=True,
    )

    artifact_id, task_id = await use_cases.ingest_video_frame(
        session_id=session_id,
        payload=payload,
        actor_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return InterviewVideoFrameIngestResponse(artifact_id=artifact_id, queued=task_id is not None, analysis_task_id=task_id)


@router.get('/{session_id:uuid}/live', response_model=InterviewLiveStateResponse)
async def get_live_state(
    session_id: UUID,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    session = await use_cases.get_session(session_id)
    await _assert_session_access(session=session, current_user=current_user, candidate_use_cases=candidate_use_cases)

    participants = ws_manager.participants(session_id)
    return InterviewLiveStateResponse(session_id=session_id, participants=participants)


@router.post('/question-bank', response_model=InterviewQuestionBankResponse, status_code=status.HTTP_201_CREATED)
async def create_question_bank_item(
    payload: InterviewQuestionBankCreateRequest,
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role not in {UserRole.ADMIN, UserRole.HR, UserRole.MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Manager/Admin can add question bank items')

    try:
        stage = InterviewStage(payload.stage)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid stage for question bank') from exc

    item = await use_cases.add_custom_question(
        actor_user_id=current_user.id,
        vacancy_id=payload.vacancy_id,
        stage=stage,
        question_text=payload.question_text,
        expected_difficulty=payload.expected_difficulty,
        metadata_json=payload.metadata_json,
    )
    await db.commit()
    return question_bank_to_schema(item)


@router.get('/question-bank', response_model=list[InterviewQuestionBankResponse])
async def list_question_bank_items(
    vacancy_id: UUID | None = Query(default=None),
    stage: str | None = Query(default=None),
    use_cases: InterviewUseCases = Depends(get_interview_use_cases),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    if stage:
        try:
            stage_enum = InterviewStage(stage)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid stage filter') from exc
    else:
        stage_enum = None
    items = await use_cases.list_custom_questions(vacancy_id=vacancy_id, stage=stage_enum)
    return [question_bank_to_schema(item) for item in items]


@ws_router.websocket('/{session_id:uuid}')
async def interview_ws(websocket: WebSocket, session_id: UUID):
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
        user_id = payload.get('sub')
        if not user_id:
            raise ValueError('Missing user id')
        user_uuid = UUID(str(user_id))
        role, is_candidate_owner = await _assert_ws_access(session_id, user_uuid)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(session_id, websocket, user_id=user_uuid, role=role)
    await ws_manager.broadcast(
        session_id,
        'participant_joined',
        {'user_id': str(user_uuid), 'role': role, 'participants': ws_manager.participants(session_id)},
        exclude_user_id=user_uuid,
    )

    try:
        await websocket.send_json(
            {
                'type': 'connected',
                'payload': {
                    'session_id': str(session_id),
                    'user_id': str(user_uuid),
                    'role': role,
                    'is_candidate_owner': is_candidate_owner,
                    'participants': ws_manager.participants(session_id),
                },
            }
        )
        while True:
            message = await websocket.receive_json()
            message_type = message.get('type')

            if message_type == 'ping':
                await websocket.send_json({'type': 'pong', 'payload': {}})
                continue

            if message_type == 'candidate_event':
                await ws_manager.broadcast(
                    session_id,
                    'event',
                    {
                        'event_type': message.get('event_type', 'unknown'),
                        'payload_json': message.get('payload_json', {}),
                        'sender_user_id': str(user_uuid),
                    },
                )
                continue

            if message_type in {'webrtc_offer', 'webrtc_answer', 'webrtc_ice', 'viewer_join'}:
                await ws_manager.broadcast(
                    session_id,
                    message_type,
                    {
                        'sender_user_id': str(user_uuid),
                        'sender_role': role,
                        'target_user_id': message.get('target_user_id'),
                        'signal': message.get('signal'),
                        'payload': message.get('payload', {}),
                    },
                    exclude_user_id=None,
                )
                continue

            if message_type == 'live_presence':
                await ws_manager.broadcast(
                    session_id,
                    'live_presence',
                    {
                        'sender_user_id': str(user_uuid),
                        'sender_role': role,
                        'payload': message.get('payload', {}),
                    },
                    exclude_user_id=user_uuid,
                )
                continue

            if message_type == 'get_live_state':
                await websocket.send_json(
                    {
                        'type': 'live_state',
                        'payload': {'session_id': str(session_id), 'participants': ws_manager.participants(session_id)},
                    }
                )
                continue

            await websocket.send_json(
                {
                    'type': 'validation_error',
                    'payload': {'detail': 'Unsupported websocket message type'},
                }
            )

    except WebSocketDisconnect:
        await ws_manager.broadcast(
            session_id,
            'participant_left',
            {'user_id': str(user_uuid), 'role': role},
            exclude_user_id=user_uuid,
        )
        ws_manager.disconnect(session_id, websocket)
    except Exception:
        await ws_manager.broadcast(
            session_id,
            'participant_left',
            {'user_id': str(user_uuid), 'role': role},
            exclude_user_id=user_uuid,
        )
        ws_manager.disconnect(session_id, websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
