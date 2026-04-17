from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    candidate_id: UUID
    document_id: UUID | None
    resume_profile_id: UUID
    parser_status: str
    structured_data: dict
    fallback_used: bool = False


class ResumeProfileResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    document_id: UUID | None
    parser_status: str
    parser_error: str | None
    structured_data: dict
    created_at: datetime
    updated_at: datetime


class ResumeManualUpdateRequest(BaseModel):
    structured_data: dict = Field(default_factory=dict)


class ResumeParseTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)

