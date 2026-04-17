from uuid import UUID

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.interview_repository import InterviewRepository
from app.schemas.feedback import FeedbackCreateRequest


class FeedbackService:
    def __init__(self, repository: FeedbackRepository, interview_repository: InterviewRepository):
        self.repository = repository
        self.interview_repository = interview_repository

    async def create(self, *, payload: FeedbackCreateRequest, author_user_id: UUID, author_role: UserRole):
        if author_role not in {UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Manager/Admin can create feedback')

        session = await self.interview_repository.get_session(payload.session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interview session not found')

        return await self.repository.create(
            session_id=payload.session_id,
            hr_user_id=author_user_id,
            manager_user_id=payload.manager_user_id,
            overall_rating=payload.overall_rating,
            strengths=payload.strengths,
            weaknesses=payload.weaknesses,
            recommendation=payload.recommendation,
            comments=payload.comments,
        )

    async def list_for_session(self, session_id: UUID):
        return await self.repository.list_for_session(session_id)
