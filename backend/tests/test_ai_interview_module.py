import sys
import types
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock
import base64

# Lightweight pgvector shim for local test environments where optional dependency is absent.
if 'pgvector.sqlalchemy' not in sys.modules:
    pgvector_module = types.ModuleType('pgvector')
    pgvector_sqlalchemy_module = types.ModuleType('pgvector.sqlalchemy')
    from sqlalchemy.types import TEXT, TypeDecorator

    class _Vector:  # pragma: no cover - test bootstrap only.
        class _VectorType(TypeDecorator):
            impl = TEXT
            cache_ok = True

        def __new__(cls, *_, **__):
            return cls._VectorType()

    pgvector_sqlalchemy_module.Vector = _Vector
    pgvector_sqlalchemy_module.cosine_distance = lambda *_args, **_kwargs: 0.0
    pgvector_module.sqlalchemy = pgvector_sqlalchemy_module
    sys.modules['pgvector'] = pgvector_module
    sys.modules['pgvector.sqlalchemy'] = pgvector_sqlalchemy_module

# Lightweight minio shim for local test environments where optional dependency is absent.
if 'minio' not in sys.modules:
    minio_module = types.ModuleType('minio')
    minio_error_module = types.ModuleType('minio.error')

    class _Minio:  # pragma: no cover - test bootstrap only.
        def __init__(self, *_, **__):
            pass

        def bucket_exists(self, *_):
            return True

        def make_bucket(self, *_):
            return None

    class _S3Error(Exception):
        pass

    minio_module.Minio = _Minio
    minio_error_module.S3Error = _S3Error
    sys.modules['minio'] = minio_module
    sys.modules['minio.error'] = minio_error_module

from app.core.rbac import Role, has_role
from app.models.enums import AnalysisStatus, InterviewMode, InterviewStage, InterviewStatus
from app.schemas.interview import InterviewAnswerRequest, InterviewCreateRequest, InterviewVideoFrameIngestRequest
from app.services.interview_service import InterviewService
from app.services.interview_state_machine import InterviewStateMachine
from app.services.question_strategy_service import QuestionStrategyService
from app.services.ws_manager import InterviewWebSocketManager


class DummyTask:
    def __init__(self, task_id: str):
        self.id = task_id


@pytest.mark.asyncio
async def test_interview_state_machine_lifecycle():
    machine = InterviewStateMachine(InterviewStatus.DRAFT)
    assert machine.to_scheduled() == InterviewStatus.SCHEDULED
    assert machine.start() == InterviewStatus.IN_PROGRESS
    assert machine.mark_intro_done() == InterviewStatus.INTRO_DONE
    assert machine.mark_theory_done() == InterviewStatus.THEORY_DONE
    assert machine.enter_ide() == InterviewStatus.IDE_IN_PROGRESS
    assert machine.await_analysis() == InterviewStatus.AWAITING_AI_ANALYSIS
    assert machine.complete() == InterviewStatus.COMPLETED
    assert machine.review() == InterviewStatus.REVIEWED


@pytest.mark.asyncio
async def test_interview_state_machine_invalid_transition():
    machine = InterviewStateMachine(InterviewStatus.SCHEDULED)
    with pytest.raises(HTTPException):
        machine.mark_theory_done()


def test_question_strategy_generates_ordered_stage_questions():
    strategy = QuestionStrategyService()
    intro = strategy.build_intro_questions(session_id='s1', candidate_name='A', vacancy_title='Backend Engineer')
    theory = strategy.build_theory_questions(session_id='s1', stack=['python', 'fastapi', 'postgres'], level='middle')

    assert [q['order_index'] for q in intro] == [1, 2, 3]
    assert all(q['stage'] == InterviewStage.INTRO for q in intro)
    assert [q['order_index'] for q in theory] == [1, 2, 3]
    assert all(q['stage'] == InterviewStage.THEORY for q in theory)
    assert strategy.should_add_follow_up(quick_score=0.2, response_time_ms=45000, difficulty=3) is True


@pytest.mark.asyncio
async def test_submit_answer_saves_answer_and_returns_next_question(monkeypatch):
    session_id = uuid4()
    candidate_id = uuid4()
    question_id = uuid4()
    next_question_id = uuid4()

    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())

    session = SimpleNamespace(
        id=session_id,
        status=InterviewStatus.IN_PROGRESS,
        mode=InterviewMode.TEXT,
        current_stage=InterviewStage.INTRO,
        candidate_id=candidate_id,
        vacancy_id=uuid4(),
    )
    question = SimpleNamespace(
        id=question_id,
        session_id=session_id,
        stage=InterviewStage.INTRO,
        question_text='Tell me about your experience',
        expected_difficulty=2,
        metadata_json={'expected_keywords': ['experience']},
    )
    next_question = SimpleNamespace(
        id=next_question_id,
        session_id=session_id,
        stage=InterviewStage.INTRO,
        question_text='What did you optimize?',
        expected_difficulty=3,
        metadata_json={},
    )
    answer = SimpleNamespace(id=uuid4(), analysis_status=AnalysisStatus.GENERATION_PENDING)

    repository.get_session.return_value = session
    repository.get_question.return_value = question
    repository.answer_exists.return_value = False
    repository.create_answer.return_value = answer
    repository.get_next_unanswered_question.return_value = next_question
    repository.create_event.return_value = SimpleNamespace(id=uuid4())

    candidate_repository = AsyncMock()
    vacancy_repository = AsyncMock()
    storage = SimpleNamespace(upload_file=lambda **_: ('documents', 'audio-1'))

    service = InterviewService(
        repository=repository,
        candidate_repository=candidate_repository,
        vacancy_repository=vacancy_repository,
        storage=storage,
    )

    monkeypatch.setattr('app.services.interview_service.celery_app.send_task', lambda *_, **__: DummyTask('task-1'))

    payload = InterviewAnswerRequest(
        question_id=question_id,
        answer_text='I have experience with distributed systems and performance tuning.',
        response_time_ms=30000,
    )

    updated_session, returned_next_question, analysis_status = await service.submit_answer(
        session_id=session_id,
        candidate_id=candidate_id,
        payload=payload,
    )

    assert updated_session.id == session_id
    assert returned_next_question.id == next_question_id
    assert analysis_status == AnalysisStatus.GENERATION_PENDING
    repository.create_answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_event_collects_anti_cheat_signal_for_risky_event(monkeypatch):
    session_id = uuid4()

    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())
    repository.get_session.return_value = SimpleNamespace(id=session_id)
    repository.create_event.return_value = SimpleNamespace(id=uuid4(), session_id=session_id)

    service = InterviewService(
        repository=repository,
        candidate_repository=AsyncMock(),
        vacancy_repository=AsyncMock(),
        storage=SimpleNamespace(upload_file=lambda **_: ('documents', 'x')),
    )
    monkeypatch.setattr('app.services.interview_service.celery_app.send_task', lambda *_, **__: DummyTask('task-anti-cheat'))

    await service.ingest_event(
        session_id=session_id,
        event_type='paste_burst',
        payload_json={'chars': 1200},
    )

    repository.create_signal.assert_awaited_once()


@pytest.mark.asyncio
async def test_finish_session_enqueues_report_generation(monkeypatch):
    session_id = uuid4()

    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())

    session = SimpleNamespace(
        id=session_id,
        status=InterviewStatus.IDE_IN_PROGRESS,
        analysis_status=AnalysisStatus.GENERATION_PENDING,
        finished_at=None,
    )

    repository.get_session.return_value = session
    repository.create_event.return_value = SimpleNamespace(id=uuid4())
    repository.upsert_assessment.return_value = SimpleNamespace(id=uuid4())

    service = InterviewService(
        repository=repository,
        candidate_repository=AsyncMock(),
        vacancy_repository=AsyncMock(),
        storage=SimpleNamespace(upload_file=lambda **_: ('documents', 'x')),
    )

    monkeypatch.setattr('app.services.interview_service.celery_app.send_task', lambda *_, **__: DummyTask('report-task-1'))

    finished, task_id = await service.finish_session(session_id)

    assert finished.status == InterviewStatus.AWAITING_AI_ANALYSIS
    assert task_id == 'report-task-1'
    repository.upsert_task_status.assert_awaited()


@pytest.mark.asyncio
async def test_finish_session_fallback_if_worker_queue_unavailable(monkeypatch):
    session_id = uuid4()

    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())

    session = SimpleNamespace(
        id=session_id,
        status=InterviewStatus.IDE_IN_PROGRESS,
        analysis_status=AnalysisStatus.GENERATION_PENDING,
        finished_at=None,
    )

    repository.get_session.return_value = session
    repository.create_event.return_value = SimpleNamespace(id=uuid4())
    repository.upsert_assessment.return_value = SimpleNamespace(id=uuid4())

    service = InterviewService(
        repository=repository,
        candidate_repository=AsyncMock(),
        vacancy_repository=AsyncMock(),
        storage=SimpleNamespace(upload_file=lambda **_: ('documents', 'x')),
    )

    def _raise_queue_error(*_, **__):
        raise RuntimeError('broker unavailable')

    monkeypatch.setattr('app.services.interview_service.celery_app.send_task', _raise_queue_error)

    finished, task_id = await service.finish_session(session_id)

    assert task_id is None
    assert finished.status == InterviewStatus.COMPLETED
    assert finished.analysis_status == AnalysisStatus.PARTIAL


@pytest.mark.asyncio
async def test_ingest_video_frame_saves_artifact_and_queues_analysis(monkeypatch):
    session_id = uuid4()
    artifact_id = uuid4()

    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())
    repository.get_session.return_value = SimpleNamespace(id=session_id)
    repository.create_media_artifact.return_value = SimpleNamespace(id=artifact_id)
    repository.create_event.return_value = SimpleNamespace(id=uuid4())

    service = InterviewService(
        repository=repository,
        candidate_repository=AsyncMock(),
        vacancy_repository=AsyncMock(),
        storage=SimpleNamespace(upload_file=lambda **_: ('documents', 'video/frame.jpg')),
    )

    monkeypatch.setattr('app.services.interview_service.celery_app.send_task', lambda *_, **__: DummyTask('video-task-1'))

    payload = InterviewVideoFrameIngestRequest(
        frame_base64=base64.b64encode(b'01234567890123456789012345678901').decode('utf-8'),
        content_type='image/jpeg',
    )

    saved_artifact_id, task_id = await service.ingest_video_frame(session_id=session_id, payload=payload)
    assert saved_artifact_id == artifact_id
    assert task_id == 'video-task-1'
    repository.create_media_artifact.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_custom_question_persists_question_bank_item():
    repository = AsyncMock()
    repository.db = SimpleNamespace(flush=AsyncMock())
    question_item = SimpleNamespace(id=uuid4(), question_text='Custom question')
    repository.create_custom_question.return_value = question_item

    service = InterviewService(
        repository=repository,
        candidate_repository=AsyncMock(),
        vacancy_repository=AsyncMock(),
        storage=SimpleNamespace(upload_file=lambda **_: ('documents', 'x')),
    )

    created = await service.add_custom_question(
        creator_user_id=uuid4(),
        vacancy_id=uuid4(),
        stage=InterviewStage.THEORY,
        question_text='Explain CAP theorem tradeoffs',
        expected_difficulty=4,
        metadata_json={'question_type': 'text'},
    )

    assert created.id == question_item.id
    repository.create_custom_question.assert_awaited_once()


@pytest.mark.asyncio
async def test_websocket_manager_broadcasts_messages():
    manager = InterviewWebSocketManager()
    session_id = uuid4()

    class DummySocket:
        def __init__(self):
            self.accepted = False
            self.messages = []

        async def accept(self):
            self.accepted = True

        async def send_json(self, payload):
            self.messages.append(payload)

    socket = DummySocket()

    await manager.connect(session_id, socket)
    await manager.broadcast(session_id, 'question_ready', {'id': 'q1'})
    manager.disconnect(session_id, socket)

    assert socket.accepted is True
    assert socket.messages == [{'type': 'question_ready', 'payload': {'id': 'q1'}}]


@pytest.mark.asyncio
async def test_require_roles_blocks_unauthorized_role():
    assert has_role({Role.HR, Role.ADMIN}, Role.CANDIDATE) is False


@pytest.mark.asyncio
async def test_create_payload_uses_required_fields():
    payload = InterviewCreateRequest(
        candidate_id=uuid4(),
        vacancy_id=uuid4(),
        mode=InterviewMode.TEXT,
    )
    assert payload.mode == InterviewMode.TEXT
