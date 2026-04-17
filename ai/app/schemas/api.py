from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class EmbeddingResponse(BaseModel):
    embedding: list[float]


class InterviewRespondRequest(BaseModel):
    history: list[dict] = Field(default_factory=list)
    mode: str = 'text'


class InterviewRespondResponse(BaseModel):
    reply: str
    voice_available: bool
    audio_base64: str | None = None
    fallback_used: bool = False


class InterviewReportRequest(BaseModel):
    transcript: list[dict] = Field(default_factory=list)


class InterviewReportResponse(BaseModel):
    report: dict
    score: float | None = None
    fallback_used: bool = False


class InterviewTestGenerateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    topic: str = Field(min_length=2, max_length=64)
    subtype: str = Field(min_length=2, max_length=64)
    difficulty: int = Field(default=2, ge=1, le=5)
    question_count: int = Field(default=8, ge=3, le=30)
    context: dict = Field(default_factory=dict)


class InterviewTestGenerateResponse(BaseModel):
    questions: list[dict]
    fallback_used: bool = False
    error: str | None = None


class VisionAnalyzeFrameRequest(BaseModel):
    frame_base64: str = Field(min_length=32)
    telemetry: dict = Field(default_factory=dict)


class VisionAnalyzeFrameResponse(BaseModel):
    metrics: dict
    risk_signals: list[dict]
    fallback_used: bool = False
    error: str | None = None


class SpeechSTTRequest(BaseModel):
    audio_base64: str = Field(min_length=16)


class SpeechSTTResponse(BaseModel):
    text: str
    fallback_used: bool = False


class SpeechTTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class SpeechTTSResponse(BaseModel):
    audio_base64: str | None = None
    voice_available: bool
    fallback_used: bool = False


class SpeechDiagnosticsResponse(BaseModel):
    stt_loaded: bool
    stt_error: str | None = None
    tts_loaded: bool
    tts_error: str | None = None


class ResumeParseResponse(BaseModel):
    status: str
    structured: dict
    raw_text: str | None = None
    fallback_used: bool = False
    error: str | None = None


class ResumeParseTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class ModelStatusResponse(BaseModel):
    resume_llm_loaded: bool
    interview_llm_loaded: bool
    embedding_loaded: bool
    stt_loaded: bool
    tts_loaded: bool
    video_analysis_loaded: bool
