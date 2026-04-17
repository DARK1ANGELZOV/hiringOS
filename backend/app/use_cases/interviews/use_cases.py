from uuid import UUID

from app.models.enums import InterviewStage
from app.schemas.interview import (
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewInviteDecisionRequest,
    InterviewRequestCreateRequest,
    InterviewRequestReviewRequest,
    InterviewScheduleUpdateRequest,
    InterviewVideoFrameIngestRequest,
    IdeSubmissionRequest,
)
from app.services.audit_service import AuditService
from app.services.interview_service import InterviewService
from app.services.notification_service import NotificationService


class InterviewUseCases:
    def __init__(
        self,
        *,
        interview_service: InterviewService,
        audit_service: AuditService,
        notification_service: NotificationService,
    ):
        self.interview_service = interview_service
        self.audit_service = audit_service
        self.notification_service = notification_service

    async def create_session(self, payload: InterviewCreateRequest, actor_user_id: UUID):
        session, _ = await self.interview_service.create_session(payload, actor_user_id=actor_user_id)
        await self.audit_service.log(
            action='interview.create',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session.id),
            metadata_json={'vacancy_id': str(payload.vacancy_id), 'candidate_id': str(payload.candidate_id)},
        )
        return session

    async def start_session(self, session_id: UUID, actor_user_id: UUID):
        session, question = await self.interview_service.start_session(session_id)
        await self.audit_service.log(
            action='interview.start',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session.id),
        )
        return session, question

    async def submit_answer(self, session_id: UUID, candidate_id: UUID, payload: InterviewAnswerRequest, actor_user_id: UUID):
        session, next_question, analysis_status = await self.interview_service.submit_answer(
            session_id=session_id,
            candidate_id=candidate_id,
            payload=payload,
        )
        await self.audit_service.log(
            action='interview.answer.submit',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session.id),
            metadata_json={'question_id': str(payload.question_id), 'analysis_status': analysis_status.value},
        )
        return session, next_question, analysis_status

    async def submit_ide(self, session_id: UUID, candidate_id: UUID, payload: IdeSubmissionRequest, actor_user_id: UUID):
        submission = await self.interview_service.submit_ide(session_id, candidate_id, payload)
        await self.audit_service.log(
            action='interview.ide.submit',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
            metadata_json={'task_id': str(payload.task_id), 'submission_id': str(submission.id)},
        )
        return submission

    async def finish_session(self, session_id: UUID, actor_user_id: UUID):
        session, task_id = await self.interview_service.finish_session(session_id)
        await self.audit_service.log(
            action='interview.finish',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session.id),
            metadata_json={'analysis_task_id': task_id},
        )
        return session, task_id

    async def get_session(self, session_id: UUID):
        return await self.interview_service.get_session(session_id)

    async def list_sessions(self, candidate_id: UUID | None = None, interviewer_id: UUID | None = None):
        return await self.interview_service.repository.list_sessions(candidate_id=candidate_id, interviewer_id=interviewer_id)

    async def create_request(self, payload: InterviewRequestCreateRequest, actor_user_id: UUID):
        item = await self.interview_service.create_request(payload=payload, actor_user_id=actor_user_id)
        await self.audit_service.log(
            action='interview.request.create',
            user_id=actor_user_id,
            entity_type='interview_request',
            entity_id=str(item.id),
            metadata_json={'candidate_id': str(item.candidate_id), 'vacancy_id': str(item.vacancy_id) if item.vacancy_id else None},
        )
        return item

    async def list_requests(
        self,
        *,
        manager_user_id: UUID | None = None,
        hr_user_id: UUID | None = None,
        candidate_id: UUID | None = None,
        status_filter: str | None = None,
    ):
        return await self.interview_service.list_requests(
            manager_user_id=manager_user_id,
            hr_user_id=hr_user_id,
            candidate_id=candidate_id,
            status_filter=status_filter,
        )

    async def review_request(self, request_id: UUID, payload: InterviewRequestReviewRequest, actor_user_id: UUID):
        item, session = await self.interview_service.review_request(request_id=request_id, payload=payload, actor_user_id=actor_user_id)
        await self.audit_service.log(
            action='interview.request.review',
            user_id=actor_user_id,
            entity_type='interview_request',
            entity_id=str(item.id),
            metadata_json={'decision': payload.decision, 'session_id': str(session.id) if session else None},
        )
        return item, session

    async def get_report(self, session_id: UUID):
        return await self.interview_service.get_report(session_id)

    async def list_questions(self, session_id: UUID):
        return await self.interview_service.list_questions(session_id)

    async def ingest_event(self, session_id: UUID, event_type: str, payload_json: dict, actor_user_id: UUID):
        event = await self.interview_service.ingest_event(session_id, event_type, payload_json)
        await self.audit_service.log(
            action='interview.event.ingest',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
            metadata_json={'event_type': event_type},
        )
        return event

    async def update_schedule(self, session_id: UUID, payload: InterviewScheduleUpdateRequest, actor_user_id: UUID):
        session = await self.interview_service.update_schedule(session_id=session_id, payload=payload)
        await self.audit_service.log(
            action='interview.schedule.update',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
            metadata_json={'scheduled_at': payload.scheduled_at.isoformat() if payload.scheduled_at else None},
        )
        return session

    async def set_invite_decision(self, session_id: UUID, payload: InterviewInviteDecisionRequest, actor_user_id: UUID):
        session = await self.interview_service.set_invite_decision(session_id=session_id, payload=payload)
        await self.audit_service.log(
            action='interview.invite.decision',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
            metadata_json={'role': payload.role, 'decision': payload.decision},
        )
        return session

    async def get_signals(self, session_id: UUID):
        return await self.interview_service.get_signals(session_id)

    async def mark_reviewed(self, session_id: UUID, actor_user_id: UUID):
        session = await self.interview_service.mark_reviewed(session_id)
        await self.audit_service.log(
            action='interview.reviewed',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
        )
        return session

    async def ingest_video_frame(self, session_id: UUID, payload: InterviewVideoFrameIngestRequest, actor_user_id: UUID):
        artifact_id, task_id = await self.interview_service.ingest_video_frame(session_id, payload)
        await self.audit_service.log(
            action='interview.video.frame.ingest',
            user_id=actor_user_id,
            entity_type='interview',
            entity_id=str(session_id),
            metadata_json={'artifact_id': str(artifact_id), 'analysis_task_id': task_id},
        )
        return artifact_id, task_id

    async def add_custom_question(
        self,
        *,
        actor_user_id: UUID,
        vacancy_id: UUID | None,
        stage: InterviewStage,
        question_text: str,
        expected_difficulty: int,
        metadata_json: dict,
    ):
        item = await self.interview_service.add_custom_question(
            creator_user_id=actor_user_id,
            vacancy_id=vacancy_id,
            stage=stage,
            question_text=question_text,
            expected_difficulty=expected_difficulty,
            metadata_json=metadata_json,
        )
        await self.audit_service.log(
            action='interview.question_bank.create',
            user_id=actor_user_id,
            entity_type='interview_question_bank',
            entity_id=str(item.id),
            metadata_json={'vacancy_id': str(vacancy_id) if vacancy_id else None, 'stage': stage.value},
        )
        return item

    async def list_custom_questions(self, *, vacancy_id: UUID | None = None, stage: InterviewStage | None = None):
        return await self.interview_service.list_custom_questions(vacancy_id=vacancy_id, stage=stage)
