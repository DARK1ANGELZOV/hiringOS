from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    AnalysisStatus,
    AntiCheatRiskLevel,
    AntiCheatSeverity,
    InterviewMode,
    InterviewQuestionType,
    InterviewStage,
    InterviewStatus,
)


class InterviewCreateRequest(BaseModel):
    candidate_id: UUID
    vacancy_id: UUID
    interviewer_id: UUID | None = None
    mode: InterviewMode = InterviewMode.TEXT
    scheduled_at: datetime | None = None
    interview_format: str = Field(default='online', max_length=32)
    meeting_link: str | None = Field(default=None, max_length=1000)
    meeting_location: str | None = Field(default=None, max_length=500)
    scheduling_comment: str | None = Field(default=None, max_length=2000)
    requested_by_manager_id: UUID | None = None


class InterviewSessionResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    vacancy_id: UUID
    interviewer_id: UUID | None
    status: InterviewStatus
    mode: InterviewMode
    current_stage: InterviewStage | None
    started_at: datetime | None
    finished_at: datetime | None
    scheduled_at: datetime | None
    interview_format: str
    meeting_link: str | None
    meeting_location: str | None
    scheduling_comment: str | None
    requested_by_manager_id: UUID | None
    candidate_invite_status: str
    manager_invite_status: str
    confirmed_candidate_at: datetime | None
    confirmed_manager_at: datetime | None
    analysis_status: AnalysisStatus
    anti_cheat_score: float
    anti_cheat_level: AntiCheatRiskLevel
    created_at: datetime
    updated_at: datetime


class InterviewProgress(BaseModel):
    answered: int
    total: int
    stage: InterviewStage | None
    progress_percent: float


class InterviewQuestionResponse(BaseModel):
    id: UUID
    session_id: UUID
    stage: InterviewStage
    order_index: int
    question_text: str
    question_type: InterviewQuestionType
    expected_difficulty: int
    metadata_json: dict
    created_at: datetime


class InterviewQuestionsListResponse(BaseModel):
    items: list[InterviewQuestionResponse]
    current_question_id: UUID | None = None


class InterviewStartResponse(BaseModel):
    session: InterviewSessionResponse
    first_question: InterviewQuestionResponse | None
    progress: InterviewProgress


class InterviewAnswerRequest(BaseModel):
    question_id: UUID
    answer_text: str | None = Field(default=None, max_length=8000)
    answer_code: str | None = None
    answer_json: dict = Field(default_factory=dict)
    response_time_ms: int | None = Field(default=None, ge=0)
    audio_base64: str | None = None
    audio_content_type: str | None = None
    telemetry: dict = Field(default_factory=dict)


class InterviewAnswerResponse(BaseModel):
    accepted: bool
    current_question_id: UUID
    next_question: InterviewQuestionResponse | None
    session_status: InterviewStatus
    stage: InterviewStage | None
    progress: InterviewProgress
    ai_analysis_status: AnalysisStatus


class InterviewFinishResponse(BaseModel):
    status: InterviewStatus
    analysis_status: AnalysisStatus
    analysis_task_id: str | None = None


class InterviewScheduleUpdateRequest(BaseModel):
    interviewer_id: UUID | None = None
    scheduled_at: datetime | None = None
    interview_format: str = Field(default='online', max_length=32)
    meeting_link: str | None = Field(default=None, max_length=1000)
    meeting_location: str | None = Field(default=None, max_length=500)
    scheduling_comment: str | None = Field(default=None, max_length=2000)
    candidate_invite_status: str = Field(default='pending', max_length=32)
    manager_invite_status: str = Field(default='pending', max_length=32)


class InterviewInviteDecisionRequest(BaseModel):
    role: str = Field(min_length=2, max_length=32)
    decision: str = Field(min_length=2, max_length=32)


class InterviewReportResponse(BaseModel):
    generation_status: AnalysisStatus
    summary_text: str | None = None
    score_total: float | None = None
    score_hard_skills: float | None = None
    score_soft_skills: float | None = None
    score_communication: float | None = None
    score_problem_solving: float | None = None
    score_code_quality: float | None = None
    score_business_thinking: float | None = None
    risk_flags_json: list[dict] = Field(default_factory=list)
    recommendations_json: list[dict] = Field(default_factory=list)
    raw_result_json: dict = Field(default_factory=dict)


class InterviewEventIngestRequest(BaseModel):
    event_type: str = Field(min_length=2, max_length=128)
    payload_json: dict = Field(default_factory=dict)


class InterviewVideoFrameIngestRequest(BaseModel):
    frame_base64: str = Field(min_length=32)
    content_type: str = Field(default='image/jpeg', max_length=128)
    captured_at: datetime | None = None
    telemetry: dict = Field(default_factory=dict)


class InterviewVideoFrameIngestResponse(BaseModel):
    artifact_id: UUID
    queued: bool
    analysis_task_id: str | None = None


class InterviewEventResponse(BaseModel):
    id: UUID
    session_id: UUID
    event_type: str
    payload_json: dict
    created_at: datetime


class IdeTaskResponse(BaseModel):
    id: UUID
    session_id: UUID
    task_title: str
    task_description: str
    starter_code: str
    tests_json: list[dict]
    constraints_json: dict
    expected_output_json: dict
    difficulty: int
    created_at: datetime


class IdeSubmissionRequest(BaseModel):
    task_id: UUID
    code_text: str = Field(min_length=1)
    execution_result_json: dict = Field(default_factory=dict)
    logs_text: str | None = None
    behavior_json: dict = Field(default_factory=dict)


class IdeSubmissionResponse(BaseModel):
    id: UUID
    task_id: UUID
    plagiarism_score: float | None
    behavior_score: float | None
    submitted_at: datetime


class AntiCheatSignalResponse(BaseModel):
    id: UUID
    signal_type: str
    severity: AntiCheatSeverity
    value_json: dict
    created_at: datetime


class InterviewSignalsResponse(BaseModel):
    risk_level: AntiCheatRiskLevel
    anti_cheat_score: float
    items: list[AntiCheatSignalResponse]


class InterviewLiveParticipant(BaseModel):
    user_id: UUID
    role: str
    joined_at: datetime


class InterviewLiveStateResponse(BaseModel):
    session_id: UUID
    participants: list[InterviewLiveParticipant]


class InterviewWSMessage(BaseModel):
    type: str
    payload: dict


class InterviewRequestCreateRequest(BaseModel):
    candidate_id: UUID
    vacancy_id: UUID | None = None
    requested_mode: InterviewMode = InterviewMode.TEXT
    requested_format: str = Field(default='online', max_length=32)
    requested_time: datetime | None = None
    comment: str | None = Field(default=None, max_length=2000)
    hr_user_id: UUID | None = None
    metadata_json: dict = Field(default_factory=dict)


class InterviewRequestReviewRequest(BaseModel):
    decision: str = Field(min_length=2, max_length=32)
    review_comment: str | None = Field(default=None, max_length=2000)
    interviewer_id: UUID | None = None
    vacancy_id: UUID | None = None
    mode: InterviewMode | None = None
    scheduled_at: datetime | None = None
    interview_format: str = Field(default='online', max_length=32)
    meeting_link: str | None = Field(default=None, max_length=1000)
    meeting_location: str | None = Field(default=None, max_length=500)
    scheduling_comment: str | None = Field(default=None, max_length=2000)


class InterviewRequestResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    vacancy_id: UUID | None
    manager_user_id: UUID
    hr_user_id: UUID | None
    requested_mode: InterviewMode
    requested_format: str
    requested_time: datetime | None
    comment: str | None
    status: str
    review_comment: str | None
    reviewed_at: datetime | None
    created_interview_session_id: UUID | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime


class InterviewSpeechDiagnosticsResponse(BaseModel):
    stt_loaded: bool
    stt_error: str | None = None
    tts_loaded: bool
    tts_error: str | None = None
