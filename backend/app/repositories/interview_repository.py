from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.models.assessment import InterviewQuestionBank
from app.models.enums import InterviewStage
from app.models.interview import (
    AntiCheatSignal,
    AsyncTaskStatus,
    IdeSubmission,
    IdeTask,
    InterviewAnswer,
    InterviewAssessment,
    InterviewEvent,
    InterviewMediaArtifact,
    InterviewQuestion,
    InterviewRequest,
    InterviewSession,
)
from app.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[InterviewSession]):
    async def create_session(self, **kwargs) -> InterviewSession:
        session = InterviewSession(**kwargs)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: UUID) -> InterviewSession | None:
        result = await self.db.execute(
            select(InterviewSession)
            .options(
                selectinload(InterviewSession.questions),
                selectinload(InterviewSession.answers),
                selectinload(InterviewSession.ide_tasks),
                selectinload(InterviewSession.assessments),
                selectinload(InterviewSession.anti_cheat_signals),
            )
            .where(InterviewSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        *,
        candidate_id: UUID | None = None,
        interviewer_id: UUID | None = None,
        limit: int = 100,
    ) -> list[InterviewSession]:
        query = select(InterviewSession).order_by(InterviewSession.created_at.desc()).limit(limit)
        if candidate_id:
            query = query.where(InterviewSession.candidate_id == candidate_id)
        if interviewer_id:
            query = query.where(InterviewSession.interviewer_id == interviewer_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_request(self, **kwargs) -> InterviewRequest:
        item = InterviewRequest(**kwargs)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_request(self, request_id: UUID) -> InterviewRequest | None:
        result = await self.db.execute(select(InterviewRequest).where(InterviewRequest.id == request_id))
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        *,
        manager_user_id: UUID | None = None,
        hr_user_id: UUID | None = None,
        candidate_id: UUID | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[InterviewRequest]:
        query = select(InterviewRequest).order_by(InterviewRequest.created_at.desc()).limit(limit)
        if manager_user_id is not None:
            query = query.where(InterviewRequest.manager_user_id == manager_user_id)
        if hr_user_id is not None:
            query = query.where(InterviewRequest.hr_user_id == hr_user_id)
        if candidate_id is not None:
            query = query.where(InterviewRequest.candidate_id == candidate_id)
        if status:
            query = query.where(InterviewRequest.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_questions(self, payloads: list[dict]) -> list[InterviewQuestion]:
        questions = [InterviewQuestion(**payload) for payload in payloads]
        self.db.add_all(questions)
        await self.db.flush()
        return questions

    async def create_question(self, **payload) -> InterviewQuestion:
        question = InterviewQuestion(**payload)
        self.db.add(question)
        await self.db.flush()
        return question

    async def get_question(self, question_id: UUID) -> InterviewQuestion | None:
        result = await self.db.execute(select(InterviewQuestion).where(InterviewQuestion.id == question_id))
        return result.scalar_one_or_none()

    async def list_questions(self, session_id: UUID, stage: InterviewStage | None = None) -> list[InterviewQuestion]:
        query = (
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.stage.asc(), InterviewQuestion.order_index.asc())
        )
        if stage:
            query = query.where(InterviewQuestion.stage == stage)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_next_unanswered_question(self, session_id: UUID, stage: InterviewStage) -> InterviewQuestion | None:
        answered_subquery = select(InterviewAnswer.question_id).where(InterviewAnswer.session_id == session_id).subquery()

        result = await self.db.execute(
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.stage == stage,
                InterviewQuestion.id.not_in(select(answered_subquery.c.question_id)),
            )
            .order_by(InterviewQuestion.order_index.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_questions(self, session_id: UUID, stage: InterviewStage | None = None) -> int:
        query = select(func.count(InterviewQuestion.id)).where(InterviewQuestion.session_id == session_id)
        if stage:
            query = query.where(InterviewQuestion.stage == stage)
        value = await self.db.scalar(query)
        return int(value or 0)

    async def count_answers(self, session_id: UUID, stage: InterviewStage | None = None) -> int:
        query = select(func.count(InterviewAnswer.id)).where(InterviewAnswer.session_id == session_id)
        if stage:
            query = query.join(InterviewQuestion, InterviewQuestion.id == InterviewAnswer.question_id).where(InterviewQuestion.stage == stage)
        value = await self.db.scalar(query)
        return int(value or 0)

    async def create_answer(self, **payload) -> InterviewAnswer:
        answer = InterviewAnswer(**payload)
        self.db.add(answer)
        await self.db.flush()
        return answer

    async def answer_exists(self, *, session_id: UUID, question_id: UUID, candidate_id: UUID) -> bool:
        result = await self.db.execute(
            select(InterviewAnswer.id).where(
                InterviewAnswer.session_id == session_id,
                InterviewAnswer.question_id == question_id,
                InterviewAnswer.candidate_id == candidate_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_answers(self, session_id: UUID) -> list[InterviewAnswer]:
        result = await self.db.execute(
            select(InterviewAnswer)
            .where(InterviewAnswer.session_id == session_id)
            .order_by(InterviewAnswer.submitted_at.asc())
        )
        return list(result.scalars().all())

    async def max_order_index(self, session_id: UUID, stage: InterviewStage) -> int:
        value = await self.db.scalar(
            select(func.max(InterviewQuestion.order_index)).where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.stage == stage,
            )
        )
        return int(value or 0)

    async def get_answer(self, answer_id: UUID) -> InterviewAnswer | None:
        result = await self.db.execute(select(InterviewAnswer).where(InterviewAnswer.id == answer_id))
        return result.scalar_one_or_none()

    async def create_event(self, **payload) -> InterviewEvent:
        event = InterviewEvent(**payload)
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_events(self, session_id: UUID, limit: int = 500) -> list[InterviewEvent]:
        result = await self.db.execute(
            select(InterviewEvent)
            .where(InterviewEvent.session_id == session_id)
            .order_by(InterviewEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def upsert_assessment(self, *, session_id: UUID, ai_model_name: str, defaults: dict) -> InterviewAssessment:
        result = await self.db.execute(
            select(InterviewAssessment).where(
                InterviewAssessment.session_id == session_id,
                InterviewAssessment.ai_model_name == ai_model_name,
            )
        )
        assessment = result.scalar_one_or_none()
        if assessment:
            for key, value in defaults.items():
                setattr(assessment, key, value)
            await self.db.flush()
            return assessment

        assessment = InterviewAssessment(session_id=session_id, ai_model_name=ai_model_name, **defaults)
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def latest_assessment(self, session_id: UUID) -> InterviewAssessment | None:
        result = await self.db.execute(
            select(InterviewAssessment)
            .where(InterviewAssessment.session_id == session_id)
            .order_by(InterviewAssessment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_signal(self, **payload) -> AntiCheatSignal:
        signal = AntiCheatSignal(**payload)
        self.db.add(signal)
        await self.db.flush()
        return signal

    async def list_signals(self, session_id: UUID, limit: int = 500) -> list[AntiCheatSignal]:
        result = await self.db.execute(
            select(AntiCheatSignal)
            .where(AntiCheatSignal.session_id == session_id)
            .order_by(AntiCheatSignal.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_ide_tasks(self, payloads: list[dict]) -> list[IdeTask]:
        tasks = [IdeTask(**payload) for payload in payloads]
        self.db.add_all(tasks)
        await self.db.flush()
        return tasks

    async def list_ide_tasks(self, session_id: UUID) -> list[IdeTask]:
        result = await self.db.execute(
            select(IdeTask)
            .where(IdeTask.session_id == session_id)
            .order_by(IdeTask.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_ide_task(self, task_id: UUID) -> IdeTask | None:
        result = await self.db.execute(select(IdeTask).where(IdeTask.id == task_id))
        return result.scalar_one_or_none()

    async def get_ide_submission(self, submission_id: UUID) -> IdeSubmission | None:
        result = await self.db.execute(select(IdeSubmission).where(IdeSubmission.id == submission_id))
        return result.scalar_one_or_none()

    async def create_ide_submission(self, **payload) -> IdeSubmission:
        submission = IdeSubmission(**payload)
        self.db.add(submission)
        await self.db.flush()
        return submission

    async def list_ide_submissions(self, session_id: UUID) -> list[IdeSubmission]:
        result = await self.db.execute(
            select(IdeSubmission)
            .join(IdeTask, IdeTask.id == IdeSubmission.task_id)
            .where(IdeTask.session_id == session_id)
            .order_by(IdeSubmission.submitted_at.asc())
        )
        return list(result.scalars().all())

    async def create_media_artifact(self, **payload) -> InterviewMediaArtifact:
        artifact = InterviewMediaArtifact(**payload)
        self.db.add(artifact)
        await self.db.flush()
        return artifact

    async def get_media_artifact(self, artifact_id: UUID) -> InterviewMediaArtifact | None:
        result = await self.db.execute(select(InterviewMediaArtifact).where(InterviewMediaArtifact.id == artifact_id))
        return result.scalar_one_or_none()

    async def list_media_artifacts(self, session_id: UUID, limit: int = 1000) -> list[InterviewMediaArtifact]:
        result = await self.db.execute(
            select(InterviewMediaArtifact)
            .where(InterviewMediaArtifact.session_id == session_id)
            .order_by(InterviewMediaArtifact.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_custom_question(self, **payload) -> InterviewQuestionBank:
        item = InterviewQuestionBank(**payload)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_custom_question(self, question_id: UUID) -> InterviewQuestionBank | None:
        result = await self.db.execute(select(InterviewQuestionBank).where(InterviewQuestionBank.id == question_id))
        return result.scalar_one_or_none()

    async def list_custom_questions(
        self,
        *,
        vacancy_id: UUID | None = None,
        creator_id: UUID | None = None,
        stage: InterviewStage | None = None,
        active_only: bool = True,
        limit: int = 200,
    ) -> list[InterviewQuestionBank]:
        query = select(InterviewQuestionBank).order_by(InterviewQuestionBank.created_at.desc()).limit(limit)
        if vacancy_id:
            query = query.where(InterviewQuestionBank.vacancy_id == vacancy_id)
        if creator_id:
            query = query.where(InterviewQuestionBank.created_by_user_id == creator_id)
        if stage:
            query = query.where(InterviewQuestionBank.stage == stage)
        if active_only:
            query = query.where(InterviewQuestionBank.is_active.is_(True))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_custom_questions_for_vacancy(
        self,
        *,
        vacancy_id: UUID,
        stage: InterviewStage,
        limit: int = 3,
    ) -> list[InterviewQuestionBank]:
        result = await self.db.execute(
            select(InterviewQuestionBank)
            .where(
                InterviewQuestionBank.is_active.is_(True),
                InterviewQuestionBank.stage == stage,
                (InterviewQuestionBank.vacancy_id == vacancy_id) | (InterviewQuestionBank.vacancy_id.is_(None)),
            )
            .order_by(InterviewQuestionBank.vacancy_id.desc(), InterviewQuestionBank.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def upsert_task_status(self, *, session_id: UUID, task_id: str, task_name: str, status: str, retries: int = 0, error_message: str | None = None) -> AsyncTaskStatus:
        result = await self.db.execute(select(AsyncTaskStatus).where(AsyncTaskStatus.task_id == task_id))
        item = result.scalar_one_or_none()
        if item:
            item.status = status
            item.retries = retries
            item.error_message = error_message
            await self.db.flush()
            return item

        item = AsyncTaskStatus(
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status=status,
            retries=retries,
            error_message=error_message,
        )
        self.db.add(item)
        await self.db.flush()
        return item
