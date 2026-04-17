from uuid import UUID

from sqlalchemy import select

from app.models.feedback import InterviewFeedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[InterviewFeedback]):
    async def create(self, **kwargs) -> InterviewFeedback:
        feedback = InterviewFeedback(**kwargs)
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def list_for_session(self, session_id: UUID) -> list[InterviewFeedback]:
        result = await self.db.execute(
            select(InterviewFeedback)
            .where(InterviewFeedback.session_id == session_id)
            .order_by(InterviewFeedback.created_at.desc())
        )
        return list(result.scalars().all())
