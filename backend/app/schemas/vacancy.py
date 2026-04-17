from datetime import datetime
from pydantic import BaseModel, Field


class VacancyCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    level: str = Field(min_length=2, max_length=64)
    department: str | None = Field(default=None, max_length=255)
    stack_json: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=5000)


class VacancyResponse(BaseModel):
    id: str
    title: str
    level: str
    department: str | None
    stack_json: list[str]
    description: str | None
    created_at: datetime
    updated_at: datetime


class VacancyMatchInfo(BaseModel):
    score_percent: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class VacancyCandidateViewResponse(VacancyResponse):
    match: VacancyMatchInfo | None = None


class VacancyApplyRequest(BaseModel):
    cover_letter_text: str | None = Field(default=None, max_length=4000)
    note: str | None = Field(default=None, max_length=2000)
    metadata_json: dict = Field(default_factory=dict)


class VacancyApplicationResponse(BaseModel):
    id: str
    vacancy_id: str
    candidate_id: str
    created_by_user_id: str | None
    status: str
    cover_letter_text: str | None
    note: str | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class VacancyApplicationStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=2, max_length=64)
    note: str | None = Field(default=None, max_length=2000)
