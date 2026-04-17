from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CandidateBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    organization_id: UUID | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = None
    city: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    citizenship: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    desired_position: str | None = Field(default=None, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    level: str | None = Field(default=None, max_length=64)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    salary_expectation: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=128)
    work_format: str | None = Field(default=None, max_length=128)
    work_schedule: str | None = Field(default=None, max_length=128)
    relocation_ready: bool | None = None
    travel_ready: bool | None = None
    status: str = Field(default='new', max_length=64)
    skills_raw: str | None = Field(default=None, max_length=8000)
    competencies_raw: str | None = Field(default=None, max_length=8000)
    languages_raw: str | None = Field(default=None, max_length=4000)
    skills: list[dict] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    languages: list[dict] = Field(default_factory=list)


class CandidateCreate(CandidateBase):
    owner_user_id: UUID | None = None


class CandidateUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    organization_id: UUID | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = None
    city: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    citizenship: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    desired_position: str | None = Field(default=None, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    level: str | None = Field(default=None, max_length=64)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    salary_expectation: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=128)
    work_format: str | None = Field(default=None, max_length=128)
    work_schedule: str | None = Field(default=None, max_length=128)
    relocation_ready: bool | None = None
    travel_ready: bool | None = None
    status: str | None = Field(default=None, max_length=64)
    status_comment: str | None = Field(default=None, max_length=2000)
    skills_raw: str | None = Field(default=None, max_length=8000)
    competencies_raw: str | None = Field(default=None, max_length=8000)
    languages_raw: str | None = Field(default=None, max_length=4000)
    skills: list[dict] | None = None
    experience: list[dict] | None = None
    education: list[dict] | None = None
    projects: list[dict] | None = None
    languages: list[dict] | None = None


class CandidateResponse(CandidateBase):
    id: UUID
    owner_user_id: UUID | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    items: list[CandidateResponse]
    total: int


class CandidateSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class CandidateSearchResult(BaseModel):
    candidate: CandidateResponse
    score: float


class CandidateSearchResponse(BaseModel):
    items: list[CandidateSearchResult]


class CandidateStatusUpdateRequest(BaseModel):
    new_status: str = Field(min_length=2, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    metadata_json: dict = Field(default_factory=dict)


class CandidateStatusHistoryResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    previous_status: str | None
    new_status: str
    changed_by_user_id: UUID | None
    comment: str | None
    metadata_json: dict
    created_at: datetime

