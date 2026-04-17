import base64
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.core.celery_app import celery_app
from app.integrations.ai_service import ai_client
from app.integrations.minio_storage import MinioStorage
from app.models.enums import (
    AnalysisStatus,
    AntiCheatSeverity,
    InterviewMode,
    InterviewStage,
    InterviewStatus,
)
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.vacancy_repository import VacancyRepository
from app.schemas.interview import (
    InterviewInviteDecisionRequest,
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewRequestCreateRequest,
    InterviewRequestReviewRequest,
    InterviewScheduleUpdateRequest,
    InterviewVideoFrameIngestRequest,
    IdeSubmissionRequest,
)
from app.services.anti_cheat_service import AntiCheatService
from app.services.interview_state_machine import InterviewStateMachine
from app.services.question_strategy_service import QuestionStrategyService
from app.services.scoring_engine_service import ScoringEngineService


class InterviewService:
    def __init__(
        self,
        *,
        repository: InterviewRepository,
        candidate_repository: CandidateRepository,
        vacancy_repository: VacancyRepository,
        storage: MinioStorage,
    ):
        self.repository = repository
        self.candidate_repository = candidate_repository
        self.vacancy_repository = vacancy_repository
        self.storage = storage
        self.question_strategy = QuestionStrategyService()
        self.scoring_engine = ScoringEngineService()
        self.anti_cheat = AntiCheatService(repository)

    async def create_session(self, payload: InterviewCreateRequest, actor_user_id: UUID) -> tuple[object, object | None]:
        candidate = await self.candidate_repository.get_by_id(payload.candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')

        vacancy = await self.vacancy_repository.get_by_id(payload.vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vacancy not found')

        interview_format = self._normalize_interview_format(payload.interview_format)

        session = await self.repository.create_session(
            candidate_id=payload.candidate_id,
            vacancy_id=payload.vacancy_id,
            interviewer_id=payload.interviewer_id or actor_user_id,
            status=InterviewStatus.DRAFT,
            mode=payload.mode,
            current_stage=None,
            scheduled_at=payload.scheduled_at,
            interview_format=interview_format,
            meeting_link=payload.meeting_link,
            meeting_location=payload.meeting_location,
            scheduling_comment=payload.scheduling_comment,
            requested_by_manager_id=payload.requested_by_manager_id,
            candidate_invite_status='pending',
            manager_invite_status='pending',
            analysis_status=AnalysisStatus.GENERATION_PENDING,
        )

        state_machine = InterviewStateMachine(session.status)
        session.status = state_machine.to_scheduled()

        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_created',
            payload_json={
                'candidate_id': str(payload.candidate_id),
                'vacancy_id': str(payload.vacancy_id),
                'interviewer_id': str(session.interviewer_id) if session.interviewer_id else None,
                'mode': payload.mode.value,
                'scheduled_at': session.scheduled_at.isoformat() if session.scheduled_at else None,
                'interview_format': session.interview_format,
            },
        )

        return session, await self._get_next_question(session.id, InterviewStage.INTRO)

    async def create_request(self, payload: InterviewRequestCreateRequest, actor_user_id: UUID):
        candidate = await self.candidate_repository.get_by_id(payload.candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate not found')

        if payload.vacancy_id:
            vacancy = await self.vacancy_repository.get_by_id(payload.vacancy_id)
            if not vacancy:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vacancy not found')

        request_item = await self.repository.create_request(
            candidate_id=payload.candidate_id,
            vacancy_id=payload.vacancy_id,
            manager_user_id=actor_user_id,
            hr_user_id=payload.hr_user_id,
            requested_mode=payload.requested_mode,
            requested_format=self._normalize_interview_format(payload.requested_format),
            requested_time=payload.requested_time,
            comment=payload.comment,
            status='pending',
            metadata_json=payload.metadata_json,
        )
        await self.repository.db.flush()
        return request_item

    async def list_requests(
        self,
        *,
        manager_user_id: UUID | None = None,
        hr_user_id: UUID | None = None,
        candidate_id: UUID | None = None,
        status_filter: str | None = None,
    ):
        return await self.repository.list_requests(
            manager_user_id=manager_user_id,
            hr_user_id=hr_user_id,
            candidate_id=candidate_id,
            status=status_filter,
        )

    async def review_request(self, request_id: UUID, payload: InterviewRequestReviewRequest, actor_user_id: UUID):
        request_item = await self.repository.get_request(request_id)
        if not request_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interview request not found')
        if request_item.status != 'pending':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Interview request already reviewed')

        decision = payload.decision.strip().lower()
        if decision not in {'approved', 'rejected'}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Decision must be approved or rejected')

        session = None
        request_item.hr_user_id = actor_user_id
        request_item.review_comment = payload.review_comment
        request_item.reviewed_at = datetime.now(timezone.utc)

        if decision == 'approved':
            vacancy_id = payload.vacancy_id or request_item.vacancy_id
            if not vacancy_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Vacancy is required for approval')
            mode = payload.mode or request_item.requested_mode
            create_payload = InterviewCreateRequest(
                candidate_id=request_item.candidate_id,
                vacancy_id=vacancy_id,
                interviewer_id=payload.interviewer_id or actor_user_id,
                mode=mode,
                scheduled_at=payload.scheduled_at or request_item.requested_time,
                interview_format=payload.interview_format or request_item.requested_format,
                meeting_link=payload.meeting_link,
                meeting_location=payload.meeting_location,
                scheduling_comment=payload.scheduling_comment or payload.review_comment,
                requested_by_manager_id=request_item.manager_user_id,
            )
            session, _ = await self.create_session(create_payload, actor_user_id=actor_user_id)
            request_item.status = 'approved'
            request_item.created_interview_session_id = session.id
            await self.repository.create_event(
                session_id=session.id,
                event_type='interview_request_approved',
                payload_json={'request_id': str(request_item.id)},
            )
        else:
            request_item.status = 'rejected'

        await self.repository.db.flush()
        return request_item, session

    async def update_schedule(self, session_id: UUID, payload: InterviewScheduleUpdateRequest):
        session = await self.get_session(session_id)
        session.interviewer_id = payload.interviewer_id or session.interviewer_id
        session.scheduled_at = payload.scheduled_at
        session.interview_format = self._normalize_interview_format(payload.interview_format)
        session.meeting_link = payload.meeting_link
        session.meeting_location = payload.meeting_location
        session.scheduling_comment = payload.scheduling_comment
        session.candidate_invite_status = payload.candidate_invite_status.strip().lower()
        session.manager_invite_status = payload.manager_invite_status.strip().lower()

        if session.status == InterviewStatus.DRAFT:
            state_machine = InterviewStateMachine(session.status)
            session.status = state_machine.to_scheduled()

        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_scheduled',
            payload_json={
                'scheduled_at': session.scheduled_at.isoformat() if session.scheduled_at else None,
                'interview_format': session.interview_format,
                'meeting_link': session.meeting_link,
                'meeting_location': session.meeting_location,
                'candidate_invite_status': session.candidate_invite_status,
                'manager_invite_status': session.manager_invite_status,
            },
        )
        await self.repository.db.flush()
        return session

    async def set_invite_decision(self, session_id: UUID, payload: InterviewInviteDecisionRequest):
        session = await self.get_session(session_id)
        role = payload.role.strip().lower()
        decision = payload.decision.strip().lower()
        if role not in {'candidate', 'manager'}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Role must be candidate or manager')
        if decision not in {'accepted', 'declined', 'pending'}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Decision must be accepted, declined or pending')

        now = datetime.now(timezone.utc)
        if role == 'candidate':
            session.candidate_invite_status = decision
            session.confirmed_candidate_at = now if decision == 'accepted' else None
        else:
            session.manager_invite_status = decision
            session.confirmed_manager_at = now if decision == 'accepted' else None

        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_invite_status_changed',
            payload_json={'role': role, 'decision': decision},
        )
        await self.repository.db.flush()
        return session

    async def start_session(self, session_id: UUID) -> tuple[object, object | None]:
        session = await self.get_session(session_id)
        state_machine = InterviewStateMachine(session.status)

        if session.status == InterviewStatus.DRAFT:
            session.status = state_machine.to_scheduled()
            state_machine = InterviewStateMachine(session.status)

        session.status = state_machine.start()
        session.current_stage = InterviewStage.INTRO
        session.started_at = datetime.now(timezone.utc)

        await self._prepare_session_content(session)
        first_question = await self._get_next_question(session.id, InterviewStage.INTRO)

        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_started',
            payload_json={'started_at': session.started_at.isoformat()},
        )
        if first_question:
            await self.repository.create_event(
                session_id=session.id,
                event_type='question_sent',
                payload_json={'question_id': str(first_question.id), 'stage': first_question.stage.value},
            )

        await self.repository.db.flush()
        return session, first_question

    async def submit_answer(self, session_id: UUID, candidate_id: UUID, payload: InterviewAnswerRequest) -> tuple[object, object | None, AnalysisStatus]:
        session = await self.get_session(session_id)
        question = await self.repository.get_question(payload.question_id)
        if not question or question.session_id != session.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found for session')

        if await self.repository.answer_exists(session_id=session.id, question_id=question.id, candidate_id=candidate_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Question already answered')

        if session.status not in {
            InterviewStatus.IN_PROGRESS,
            InterviewStatus.INTRO_DONE,
            InterviewStatus.THEORY_DONE,
            InterviewStatus.IDE_IN_PROGRESS,
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Session is not accepting answers')

        audio_artifact_id = None
        answer_text = payload.answer_text

        if payload.audio_base64:
            audio_artifact_id = await self._store_audio_artifact(session_id, payload.audio_base64, payload.audio_content_type)
            if not answer_text:
                answer_text = '[voice_answer_pending_transcription]'

        quick_score = self.scoring_engine.quick_text_score(
            answer_text=answer_text,
            expected_keywords=(question.metadata_json or {}).get('expected_keywords'),
        )

        answer = await self.repository.create_answer(
            question_id=question.id,
            session_id=session.id,
            candidate_id=candidate_id,
            answer_text=answer_text,
            answer_audio_file_id=audio_artifact_id,
            answer_code=payload.answer_code,
            answer_json=payload.answer_json,
            response_time_ms=payload.response_time_ms,
            quick_score=quick_score,
            analysis_status=AnalysisStatus.GENERATION_PENDING,
        )

        await self.repository.create_event(
            session_id=session.id,
            event_type='answer_submitted',
            payload_json={
                'question_id': str(question.id),
                'answer_id': str(answer.id),
                'stage': question.stage.value,
                'quick_score': quick_score,
            },
        )

        await self._ingest_telemetry_signals(session.id, payload.telemetry)

        analyze_task = celery_app.send_task('interview.analyze_answer', args=[str(answer.id)])
        await self.repository.upsert_task_status(
            session_id=session.id,
            task_id=analyze_task.id,
            task_name='interview.analyze_answer',
            status='queued',
        )

        if audio_artifact_id and payload.answer_text is None:
            stt_task = celery_app.send_task('interview.transcribe_answer_audio', args=[str(answer.id)])
            await self.repository.upsert_task_status(
                session_id=session.id,
                task_id=stt_task.id,
                task_name='interview.transcribe_answer_audio',
                status='queued',
            )

        next_question = await self._pick_next_question_after_answer(session, question, quick_score, payload.response_time_ms)

        if next_question and session.mode in {InterviewMode.VOICE, InterviewMode.MIXED}:
            tts_task = celery_app.send_task('interview.generate_question_tts', args=[str(session.id), str(next_question.id)])
            await self.repository.upsert_task_status(
                session_id=session.id,
                task_id=tts_task.id,
                task_name='interview.generate_question_tts',
                status='queued',
            )

        await self.repository.db.flush()
        return session, next_question, answer.analysis_status

    async def submit_ide(self, session_id: UUID, candidate_id: UUID, payload: IdeSubmissionRequest):
        session = await self.get_session(session_id)
        task = await self.repository.get_ide_task(payload.task_id)
        if not task or task.session_id != session.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='IDE task not found for session')

        behavior_score = self._behavior_score(payload.behavior_json)
        submission = await self.repository.create_ide_submission(
            task_id=task.id,
            candidate_id=candidate_id,
            code_text=payload.code_text,
            execution_result_json=payload.execution_result_json,
            logs_text=payload.logs_text,
            behavior_score=behavior_score,
        )

        await self.repository.create_event(
            session_id=session.id,
            event_type='ide_task_submitted',
            payload_json={
                'task_id': str(task.id),
                'submission_id': str(submission.id),
                'behavior_score': behavior_score,
            },
        )

        plagiarism_task = celery_app.send_task('interview.check_plagiarism', args=[str(submission.id)])
        await self.repository.upsert_task_status(
            session_id=session.id,
            task_id=plagiarism_task.id,
            task_name='interview.check_plagiarism',
            status='queued',
        )

        await self._ingest_behavior_signals(session.id, payload.behavior_json)
        await self.repository.db.flush()
        return submission

    async def finish_session(self, session_id: UUID) -> tuple[object, str | None]:
        session = await self.get_session(session_id)

        if session.status not in {
            InterviewStatus.IDE_IN_PROGRESS,
            InterviewStatus.THEORY_DONE,
            InterviewStatus.IN_PROGRESS,
            InterviewStatus.INTRO_DONE,
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Session cannot be finished from current status')

        state_machine = InterviewStateMachine(session.status)

        if session.status == InterviewStatus.INTRO_DONE:
            session.status = state_machine.mark_theory_done()
            state_machine = InterviewStateMachine(session.status)
            session.status = state_machine.enter_ide()
            state_machine = InterviewStateMachine(session.status)

        if session.status == InterviewStatus.THEORY_DONE:
            session.status = state_machine.enter_ide()
            state_machine = InterviewStateMachine(session.status)

        if session.status == InterviewStatus.IN_PROGRESS:
            session.status = state_machine.mark_intro_done()
            state_machine = InterviewStateMachine(session.status)
            session.status = state_machine.mark_theory_done()
            state_machine = InterviewStateMachine(session.status)
            session.status = state_machine.enter_ide()
            state_machine = InterviewStateMachine(session.status)

        session.status = state_machine.await_analysis()
        session.finished_at = datetime.now(timezone.utc)

        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_finished',
            payload_json={'finished_at': session.finished_at.isoformat()},
        )

        await self.repository.upsert_assessment(
            session_id=session.id,
            ai_model_name='local-llm',
            defaults={
                'raw_result_json': {},
                'summary_text': None,
                'risk_flags_json': [],
                'recommendations_json': [],
                'generation_status': AnalysisStatus.GENERATION_PENDING,
            },
        )

        task_id: str | None = None
        try:
            report_task = celery_app.send_task('interview.generate_report', args=[str(session.id)])
            task_id = report_task.id
            await self.repository.upsert_task_status(
                session_id=session.id,
                task_id=report_task.id,
                task_name='interview.generate_report',
                status='queued',
            )
            await self.repository.create_event(
                session_id=session.id,
                event_type='ai_analysis_requested',
                payload_json={'task_id': task_id},
            )
        except Exception as exc:
            session.analysis_status = AnalysisStatus.PARTIAL
            session.status = InterviewStatus.COMPLETED
            await self.repository.create_event(
                session_id=session.id,
                event_type='report_failed',
                payload_json={'reason': str(exc)},
            )

        await self.repository.db.flush()
        return session, task_id

    async def get_report(self, session_id: UUID):
        session = await self.get_session(session_id)
        assessment = await self.repository.latest_assessment(session.id)
        return session, assessment

    async def list_questions(self, session_id: UUID):
        session = await self.get_session(session_id)
        questions = await self.repository.list_questions(session.id)
        current = await self._resolve_current_question(session)
        return questions, current

    async def ingest_event(self, session_id: UUID, event_type: str, payload_json: dict):
        session = await self.get_session(session_id)
        event = await self.repository.create_event(
            session_id=session.id,
            event_type=event_type,
            payload_json=payload_json,
        )

        severity = self._signal_severity_from_event(event_type, payload_json)
        if severity is not None:
            await self.anti_cheat.collect_signal(
                session_id=session.id,
                signal_type=event_type,
                severity=severity,
                value_json=payload_json,
            )
            celery_app.send_task('interview.aggregate_anti_cheat', args=[str(session.id)])

        await self.repository.db.flush()
        return event

    async def get_signals(self, session_id: UUID):
        session = await self.get_session(session_id)
        score, risk = await self.anti_cheat.aggregate_signals(session.id)
        signals = await self.repository.list_signals(session.id)
        return score, risk, signals

    async def ingest_video_frame(self, session_id: UUID, payload: InterviewVideoFrameIngestRequest) -> tuple[UUID, str | None]:
        session = await self.get_session(session_id)
        raw_frame = self._decode_base64_payload(payload.frame_base64, field_name='frame_base64')

        extension = 'jpg'
        if 'png' in payload.content_type.lower():
            extension = 'png'

        bucket, object_key = self.storage.upload_file(
            filename=f'interview_video_frame_{session.id}.{extension}',
            data=raw_frame,
            content_type=payload.content_type,
        )
        artifact = await self.repository.create_media_artifact(
            session_id=session.id,
            bucket=bucket,
            object_key=object_key,
            content_type=payload.content_type,
            size_bytes=len(raw_frame),
        )

        await self.repository.create_event(
            session_id=session.id,
            event_type='video_frame_received',
            payload_json={
                'artifact_id': str(artifact.id),
                'captured_at': payload.captured_at.isoformat() if payload.captured_at else None,
                'telemetry': payload.telemetry,
            },
        )

        task_id: str | None = None
        try:
            task = celery_app.send_task('interview.analyze_video_frame', args=[str(session.id), str(artifact.id), payload.telemetry])
            task_id = task.id
            await self.repository.upsert_task_status(
                session_id=session.id,
                task_id=task_id,
                task_name='interview.analyze_video_frame',
                status='queued',
            )
        except Exception:
            # Degraded mode: keep interview progressing even when video analyzer is down.
            task_id = None

        await self.repository.db.flush()
        return artifact.id, task_id

    async def add_custom_question(
        self,
        *,
        creator_user_id: UUID,
        vacancy_id: UUID | None,
        stage: InterviewStage,
        question_text: str,
        expected_difficulty: int,
        metadata_json: dict,
    ):
        item = await self.repository.create_custom_question(
            created_by_user_id=creator_user_id,
            vacancy_id=vacancy_id,
            stage=stage,
            question_text=question_text,
            expected_difficulty=expected_difficulty,
            metadata_json=metadata_json,
            is_active=True,
        )
        await self.repository.db.flush()
        return item

    async def list_custom_questions(self, *, vacancy_id: UUID | None = None, stage: InterviewStage | None = None):
        return await self.repository.list_custom_questions(vacancy_id=vacancy_id, stage=stage, active_only=True, limit=300)

    async def get_session(self, session_id: UUID):
        session = await self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interview session not found')
        return session

    async def mark_reviewed(self, session_id: UUID):
        session = await self.get_session(session_id)
        state_machine = InterviewStateMachine(session.status)
        session.status = state_machine.review()
        await self.repository.create_event(
            session_id=session.id,
            event_type='interview_reviewed',
            payload_json={},
        )
        await self.repository.db.flush()
        return session

    async def _prepare_session_content(self, session) -> None:
        existing_questions = await self.repository.count_questions(session.id)
        if existing_questions == 0:
            candidate = await self.candidate_repository.get_by_id(session.candidate_id)
            vacancy = await self.vacancy_repository.get_by_id(session.vacancy_id)
            if not candidate or not vacancy:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Candidate or vacancy not found')

            questions_payload: list[dict] = []

            intro = self.question_strategy.build_intro_questions(
                session_id=str(session.id),
                candidate_name=candidate.full_name,
                vacancy_title=vacancy.title,
            )
            theory = self.question_strategy.build_theory_questions(
                session_id=str(session.id),
                stack=vacancy.stack_json,
                level=vacancy.level,
            )

            custom_intro = await self.repository.list_custom_questions_for_vacancy(
                vacancy_id=vacancy.id,
                stage=InterviewStage.INTRO,
                limit=2,
            )
            custom_theory = await self.repository.list_custom_questions_for_vacancy(
                vacancy_id=vacancy.id,
                stage=InterviewStage.THEORY,
                limit=2,
            )

            if custom_intro:
                intro.extend(
                    [
                        {
                            'stage': InterviewStage.INTRO,
                            'order_index': len(intro) + idx + 1,
                            'question_text': item.question_text,
                            'question_type': item.metadata_json.get('question_type', 'text'),
                            'expected_difficulty': item.expected_difficulty,
                            'metadata_json': {
                                **(item.metadata_json or {}),
                                'source': 'manager_custom',
                                'bank_question_id': str(item.id),
                            },
                        }
                        for idx, item in enumerate(custom_intro)
                    ]
                )

            if custom_theory:
                theory.extend(
                    [
                        {
                            'stage': InterviewStage.THEORY,
                            'order_index': len(theory) + idx + 1,
                            'question_text': item.question_text,
                            'question_type': item.metadata_json.get('question_type', 'text'),
                            'expected_difficulty': item.expected_difficulty,
                            'metadata_json': {
                                **(item.metadata_json or {}),
                                'source': 'manager_custom',
                                'bank_question_id': str(item.id),
                            },
                        }
                        for idx, item in enumerate(custom_theory)
                    ]
                )

            for payload in [*intro, *theory]:
                payload['session_id'] = session.id
                questions_payload.append(payload)

            await self.repository.create_questions(questions_payload)

            ide_tasks_payload = self.question_strategy.build_ide_tasks(
                session_id=str(session.id),
                stack=vacancy.stack_json,
                level=vacancy.level,
            )
            for payload in ide_tasks_payload:
                payload['session_id'] = session.id

            await self.repository.create_ide_tasks(ide_tasks_payload)

    async def _pick_next_question_after_answer(self, session, question, quick_score: float, response_time_ms: int | None):
        stage = question.stage
        next_question = await self.repository.get_next_unanswered_question(session.id, stage)

        if self.question_strategy.should_add_follow_up(
            quick_score=quick_score,
            response_time_ms=response_time_ms,
            difficulty=question.expected_difficulty,
        ) and not next_question:
            next_idx = await self.repository.max_order_index(session.id, stage) + 1
            follow_up_payload = self.question_strategy.build_follow_up_question(
                session_id=str(session.id),
                stage=stage,
                order_index=next_idx,
                base_question=question.question_text,
            )
            follow_up_payload['session_id'] = session.id
            next_question = await self.repository.create_question(**follow_up_payload)

        if next_question:
            await self.repository.create_event(
                session_id=session.id,
                event_type='question_sent',
                payload_json={'question_id': str(next_question.id), 'stage': stage.value},
            )
            return next_question

        state_machine = InterviewStateMachine(session.status)

        if stage == InterviewStage.INTRO:
            session.status = state_machine.mark_intro_done()
            session.current_stage = InterviewStage.THEORY
            await self.repository.create_event(
                session_id=session.id,
                event_type='stage_completed',
                payload_json={'stage': InterviewStage.INTRO.value},
            )
            return await self.repository.get_next_unanswered_question(session.id, InterviewStage.THEORY)

        if stage == InterviewStage.THEORY:
            session.status = state_machine.mark_theory_done()
            state_machine = InterviewStateMachine(session.status)
            session.status = state_machine.enter_ide()
            session.current_stage = InterviewStage.IDE
            await self.repository.create_event(
                session_id=session.id,
                event_type='stage_completed',
                payload_json={'stage': InterviewStage.THEORY.value},
            )
            await self.repository.create_event(
                session_id=session.id,
                event_type='ide_task_started',
                payload_json={'tasks_total': len(await self.repository.list_ide_tasks(session.id))},
            )
            return None

        return None

    async def _resolve_current_question(self, session):
        if session.current_stage:
            question = await self.repository.get_next_unanswered_question(session.id, session.current_stage)
            if question:
                return question

        for stage in (InterviewStage.INTRO, InterviewStage.THEORY):
            question = await self.repository.get_next_unanswered_question(session.id, stage)
            if question:
                return question

        return None

    async def _get_next_question(self, session_id: UUID, stage: InterviewStage):
        return await self.repository.get_next_unanswered_question(session_id, stage)

    async def _store_audio_artifact(self, session_id: UUID, audio_base64: str, content_type: str | None) -> UUID:
        raw = self._decode_base64_payload(audio_base64, field_name='audio_base64')

        extension = 'wav' if 'wav' in (content_type or '').lower() else 'webm'
        bucket, object_key = self.storage.upload_file(
            filename=f'interview_answer_{session_id}.{extension}',
            data=raw,
            content_type=content_type or 'audio/wav',
        )
        artifact = await self.repository.create_media_artifact(
            session_id=session_id,
            bucket=bucket,
            object_key=object_key,
            content_type=content_type or 'audio/wav',
            size_bytes=len(raw),
        )
        return artifact.id

    async def _ingest_telemetry_signals(self, session_id: UUID, telemetry: dict) -> None:
        if not telemetry:
            return

        signal_candidates: list[tuple[str, AntiCheatSeverity, dict]] = []

        if telemetry.get('focus_blur_count', 0) >= 3:
            signal_candidates.append(('focus_blur', AntiCheatSeverity.MEDIUM, telemetry))
        if telemetry.get('tab_switch_count', 0) >= 4:
            signal_candidates.append(('tab_switch', AntiCheatSeverity.MEDIUM, telemetry))
        if telemetry.get('paste_chars', 0) >= 300:
            signal_candidates.append(('paste_burst', AntiCheatSeverity.HIGH, telemetry))
        if telemetry.get('typing_spike', False):
            signal_candidates.append(('typing_anomaly', AntiCheatSeverity.MEDIUM, telemetry))

        for signal_type, severity, value in signal_candidates:
            await self.anti_cheat.collect_signal(
                session_id=session_id,
                signal_type=signal_type,
                severity=severity,
                value_json=value,
            )

    async def _ingest_behavior_signals(self, session_id: UUID, behavior_json: dict) -> None:
        if not behavior_json:
            return

        if behavior_json.get('sudden_large_paste', False):
            await self.anti_cheat.collect_signal(
                session_id=session_id,
                signal_type='ide_behavior',
                severity=AntiCheatSeverity.HIGH,
                value_json=behavior_json,
            )
        elif behavior_json.get('rapid_submit', False):
            await self.anti_cheat.collect_signal(
                session_id=session_id,
                signal_type='session_anomaly',
                severity=AntiCheatSeverity.MEDIUM,
                value_json=behavior_json,
            )

    def _behavior_score(self, behavior_json: dict) -> float:
        if not behavior_json:
            return 0.7

        base = 0.8
        if behavior_json.get('sudden_large_paste'):
            base -= 0.3
        if behavior_json.get('rapid_submit'):
            base -= 0.2
        if behavior_json.get('reruns', 0) >= 3:
            base += 0.1

        return max(0.0, min(round(base, 4), 1.0))

    def _signal_severity_from_event(self, event_type: str, payload: dict) -> AntiCheatSeverity | None:
        if event_type in {'focus_blur', 'tab_switch'}:
            return AntiCheatSeverity.MEDIUM
        if event_type == 'paste_burst':
            return AntiCheatSeverity.HIGH
        if event_type in {'voice_anomaly', 'plagiarism'}:
            return AntiCheatSeverity.HIGH
        if event_type == 'session_anomaly':
            if payload.get('critical', False):
                return AntiCheatSeverity.CRITICAL
            return AntiCheatSeverity.HIGH
        return None

    @staticmethod
    def _decode_base64_payload(value: str, *, field_name: str) -> bytes:
        clean_value = value
        if ',' in clean_value and clean_value.strip().startswith('data:'):
            clean_value = clean_value.split(',', 1)[1]
        try:
            return base64.b64decode(clean_value)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Invalid {field_name} payload: {exc}') from exc

    @staticmethod
    def _normalize_interview_format(value: str) -> str:
        normalized = (value or 'online').strip().lower()
        allowed = {'online', 'offline', 'phone'}
        if normalized not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Interview format must be online, offline or phone')
        return normalized
