from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeTestQuestionCreate(BaseModel):
    question_text: str = Field(min_length=5, max_length=4000)
    question_type: str = Field(default='single_choice', min_length=3, max_length=64)
    options_json: list[dict] = Field(default_factory=list)
    correct_answer_json: dict = Field(default_factory=dict)
    explanation: str | None = Field(default=None, max_length=4000)
    points: int = Field(default=1, ge=1, le=20)
    metadata_json: dict = Field(default_factory=dict)


class KnowledgeTestCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    topic: str = Field(min_length=2, max_length=64)
    subtype: str = Field(min_length=2, max_length=64)
    difficulty: int = Field(default=2, ge=1, le=5)
    company_scope: str | None = Field(default=None, max_length=255)
    questions: list[KnowledgeTestQuestionCreate] = Field(default_factory=list)


class KnowledgeTestGenerateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    topic: str = Field(min_length=2, max_length=64)
    subtype: str = Field(min_length=2, max_length=64)
    difficulty: int = Field(default=2, ge=1, le=5)
    question_count: int = Field(default=8, ge=3, le=30)
    company_scope: str | None = Field(default=None, max_length=255)
    context: dict = Field(default_factory=dict)


class KnowledgeTestQuestionResponse(BaseModel):
    id: UUID
    order_index: int
    question_text: str
    question_type: str
    options_json: list[dict]
    explanation: str | None
    points: int
    metadata_json: dict


class KnowledgeTestResponse(BaseModel):
    id: UUID
    created_by_user_id: UUID
    title: str
    topic: str
    subtype: str
    difficulty: int
    is_ai_generated: bool
    is_custom: bool
    company_scope: str | None
    config_json: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeTestDetailResponse(KnowledgeTestResponse):
    questions: list[KnowledgeTestQuestionResponse]


class KnowledgeTestAttemptStartRequest(BaseModel):
    session_id: UUID | None = None


class KnowledgeTestAttemptResponse(BaseModel):
    id: UUID
    test_id: UUID
    candidate_id: UUID
    session_id: UUID | None
    status: str
    score: float | None
    max_score: float | None
    started_at: datetime
    finished_at: datetime | None
    analysis_json: dict


class KnowledgeTestAnswerSubmitRequest(BaseModel):
    question_id: UUID
    answer_json: dict = Field(default_factory=dict)


class KnowledgeTestAnswerResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    question_id: UUID
    answer_json: dict
    is_correct: bool | None
    points_earned: float
    submitted_at: datetime


class KnowledgeTestFinishResponse(BaseModel):
    attempt: KnowledgeTestAttemptResponse
    answered_count: int
    total_questions: int


class KnowledgeTestListResponse(BaseModel):
    items: list[KnowledgeTestResponse]


class InterviewQuestionBankCreateRequest(BaseModel):
    vacancy_id: UUID | None = None
    stage: str = Field(min_length=3, max_length=32)
    question_text: str = Field(min_length=5, max_length=4000)
    expected_difficulty: int = Field(default=2, ge=1, le=5)
    metadata_json: dict = Field(default_factory=dict)


class InterviewQuestionBankResponse(BaseModel):
    id: UUID
    created_by_user_id: UUID
    vacancy_id: UUID | None
    stage: str
    question_text: str
    expected_difficulty: int
    metadata_json: dict
    is_active: bool
    created_at: datetime
