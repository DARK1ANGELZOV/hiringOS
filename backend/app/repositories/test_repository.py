from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.assessment import KnowledgeTest, KnowledgeTestAnswer, KnowledgeTestAttempt, KnowledgeTestQuestion
from app.repositories.base import BaseRepository


class KnowledgeTestRepository(BaseRepository[KnowledgeTest]):
    async def create_test(self, **payload) -> KnowledgeTest:
        item = KnowledgeTest(**payload)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_test(self, test_id: UUID) -> KnowledgeTest | None:
        result = await self.db.execute(
            select(KnowledgeTest)
            .options(selectinload(KnowledgeTest.questions))
            .where(KnowledgeTest.id == test_id)
        )
        return result.scalar_one_or_none()

    async def list_tests(
        self,
        *,
        topic: str | None = None,
        subtype: str | None = None,
        created_by_user_id: UUID | None = None,
        active_only: bool = True,
        limit: int = 200,
    ) -> list[KnowledgeTest]:
        query = select(KnowledgeTest).order_by(KnowledgeTest.created_at.desc()).limit(limit)
        if topic:
            query = query.where(KnowledgeTest.topic == topic)
        if subtype:
            query = query.where(KnowledgeTest.subtype == subtype)
        if created_by_user_id:
            query = query.where(KnowledgeTest.created_by_user_id == created_by_user_id)
        if active_only:
            query = query.where(KnowledgeTest.is_active.is_(True))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_questions(self, payloads: list[dict]) -> list[KnowledgeTestQuestion]:
        questions = [KnowledgeTestQuestion(**payload) for payload in payloads]
        self.db.add_all(questions)
        await self.db.flush()
        return questions

    async def list_questions(self, test_id: UUID) -> list[KnowledgeTestQuestion]:
        result = await self.db.execute(
            select(KnowledgeTestQuestion)
            .where(KnowledgeTestQuestion.test_id == test_id)
            .order_by(KnowledgeTestQuestion.order_index.asc())
        )
        return list(result.scalars().all())

    async def get_question(self, question_id: UUID) -> KnowledgeTestQuestion | None:
        result = await self.db.execute(select(KnowledgeTestQuestion).where(KnowledgeTestQuestion.id == question_id))
        return result.scalar_one_or_none()

    async def start_attempt(self, **payload) -> KnowledgeTestAttempt:
        attempt = KnowledgeTestAttempt(**payload)
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    async def get_attempt(self, attempt_id: UUID) -> KnowledgeTestAttempt | None:
        result = await self.db.execute(
            select(KnowledgeTestAttempt)
            .options(selectinload(KnowledgeTestAttempt.answers), selectinload(KnowledgeTestAttempt.test))
            .where(KnowledgeTestAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def list_attempts(
        self,
        *,
        test_id: UUID | None = None,
        candidate_id: UUID | None = None,
        limit: int = 200,
    ) -> list[KnowledgeTestAttempt]:
        query = select(KnowledgeTestAttempt).order_by(KnowledgeTestAttempt.created_at.desc()).limit(limit)
        if test_id:
            query = query.where(KnowledgeTestAttempt.test_id == test_id)
        if candidate_id:
            query = query.where(KnowledgeTestAttempt.candidate_id == candidate_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def upsert_answer(
        self,
        *,
        attempt_id: UUID,
        question_id: UUID,
        answer_json: dict,
        is_correct: bool | None,
        points_earned: float,
    ) -> KnowledgeTestAnswer:
        result = await self.db.execute(
            select(KnowledgeTestAnswer).where(
                KnowledgeTestAnswer.attempt_id == attempt_id,
                KnowledgeTestAnswer.question_id == question_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.answer_json = answer_json
            item.is_correct = is_correct
            item.points_earned = points_earned
            item.submitted_at = datetime.now(timezone.utc)
            await self.db.flush()
            return item

        item = KnowledgeTestAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            answer_json=answer_json,
            is_correct=is_correct,
            points_earned=points_earned,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def list_attempt_answers(self, attempt_id: UUID) -> list[KnowledgeTestAnswer]:
        result = await self.db.execute(
            select(KnowledgeTestAnswer)
            .where(KnowledgeTestAnswer.attempt_id == attempt_id)
            .order_by(KnowledgeTestAnswer.submitted_at.asc())
        )
        return list(result.scalars().all())

    async def finish_attempt(self, attempt: KnowledgeTestAttempt, *, score: float, max_score: float, analysis_json: dict) -> KnowledgeTestAttempt:
        attempt.status = 'completed'
        attempt.score = score
        attempt.max_score = max_score
        attempt.analysis_json = analysis_json
        attempt.finished_at = datetime.now(timezone.utc)
        await self.db.flush()
        return attempt

    async def count_answers(self, attempt_id: UUID) -> int:
        value = await self.db.scalar(select(func.count(KnowledgeTestAnswer.id)).where(KnowledgeTestAnswer.attempt_id == attempt_id))
        return int(value or 0)
