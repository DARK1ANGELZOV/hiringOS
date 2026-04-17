from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_feedback_service
from app.api.serializers import feedback_to_schema
from app.core.database import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix='/feedback', tags=['feedback'])


@router.post('', response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreateRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = await feedback_service.create(
        payload=payload,
        author_user_id=UUID(str(current_user.id)),
        author_role=current_user.role,
    )
    await db.commit()
    return feedback_to_schema(feedback)


@router.get('', response_model=list[FeedbackResponse])
async def list_feedback(
    session_id: UUID = Query(...),
    feedback_service: FeedbackService = Depends(get_feedback_service),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    items = await feedback_service.list_for_session(session_id)
    return [feedback_to_schema(item) for item in items]
