from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    session_id: UUID
    manager_user_id: UUID | None = None
    overall_rating: int = Field(ge=1, le=5)
    strengths: str = Field(min_length=1, max_length=4000)
    weaknesses: str = Field(min_length=1, max_length=4000)
    recommendation: str = Field(min_length=1, max_length=64)
    comments: str | None = Field(default=None, max_length=4000)


class FeedbackResponse(BaseModel):
    id: UUID
    session_id: UUID
    hr_user_id: UUID
    manager_user_id: UUID | None
    overall_rating: int
    strengths: str
    weaknesses: str
    recommendation: str
    comments: str | None
    created_at: datetime
