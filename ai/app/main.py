from time import perf_counter

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import get_settings
from app.core.metrics import (
    AI_HTTP_REQUEST_DURATION_SECONDS,
    AI_HTTP_REQUESTS_TOTAL,
    AI_RESUME_PARSE_EVENTS_TOTAL,
    metrics_content_type,
    metrics_payload,
)
from app.core.speech import STTService, TTSService
from app.schemas.api import (
    EmbeddingRequest,
    EmbeddingResponse,
    InterviewReportRequest,
    InterviewReportResponse,
    InterviewRespondRequest,
    InterviewRespondResponse,
    InterviewTestGenerateRequest,
    InterviewTestGenerateResponse,
    ModelStatusResponse,
    ResumeParseResponse,
    ResumeParseTextRequest,
    SpeechDiagnosticsResponse,
    SpeechSTTRequest,
    SpeechSTTResponse,
    SpeechTTSRequest,
    SpeechTTSResponse,
    VisionAnalyzeFrameRequest,
    VisionAnalyzeFrameResponse,
)
from embeddings.service import EmbeddingService
from interview_ai.engine import InterviewAIService
from interview_ai.video_analyzer import VideoAnalyzerService
from resume_parser.extractor import extract_text_from_file
from resume_parser.parser import ResumeParserService

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug, default_response_class=ORJSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

resume_service = ResumeParserService()
interview_service = InterviewAIService()
video_analyzer_service = VideoAnalyzerService()
embedding_service = EmbeddingService()
stt_service = STTService()
tts_service = TTSService()


@app.middleware('http')
async def metrics_middleware(request, call_next):
    started = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - started
    method = request.method.upper()
    path = request.url.path
    status_code = str(response.status_code)
    AI_HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status_code).inc()
    AI_HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
    return response


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}


@app.get('/models/status', response_model=ModelStatusResponse)
async def model_status():
    return ModelStatusResponse(
        resume_llm_loaded=resume_service.is_loaded,
        interview_llm_loaded=interview_service.is_loaded,
        embedding_loaded=embedding_service.is_loaded,
        stt_loaded=stt_service.is_loaded,
        tts_loaded=tts_service.is_loaded,
        video_analysis_loaded=video_analyzer_service.is_loaded,
    )


@app.post('/resume/parse', response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)):
    content = await file.read()
    text = extract_text_from_file(file.filename or 'resume.pdf', content)
    structured, fallback_used, error = resume_service.parse(text)
    status_value = 'success' if not fallback_used else 'fallback'
    AI_RESUME_PARSE_EVENTS_TOTAL.labels(result=status_value).inc()
    return ResumeParseResponse(
        status=status_value,
        structured=structured,
        raw_text=text[: settings.max_resume_chars],
        fallback_used=fallback_used,
        error=error,
    )


@app.post('/resume/parse-text', response_model=ResumeParseResponse)
async def parse_resume_text(payload: ResumeParseTextRequest):
    text = payload.text[: settings.max_resume_chars]
    structured, fallback_used, error = resume_service.parse(text)
    status_value = 'success' if not fallback_used else 'fallback'
    AI_RESUME_PARSE_EVENTS_TOTAL.labels(result=status_value).inc()
    return ResumeParseResponse(
        status=status_value,
        structured=structured,
        raw_text=text,
        fallback_used=fallback_used,
        error=error,
    )


@app.post('/embeddings/vectorize', response_model=EmbeddingResponse)
async def vectorize(payload: EmbeddingRequest):
    vector = embedding_service.vectorize(payload.text)
    return EmbeddingResponse(embedding=vector)


@app.post('/interview/respond', response_model=InterviewRespondResponse)
async def interview_respond(payload: InterviewRespondRequest):
    reply, fallback_used, error = interview_service.respond(payload.history, payload.mode)
    if error:
        raise HTTPException(status_code=503, detail={'code': 'ai_unavailable', 'message': error})

    audio_base64 = None
    voice_available = False
    if payload.mode in {'voice', 'mixed'}:
        audio_base64, tts_fallback, _ = tts_service.synthesize(reply)
        voice_available = not tts_fallback and audio_base64 is not None

    return InterviewRespondResponse(
        reply=reply,
        voice_available=voice_available,
        audio_base64=audio_base64,
        fallback_used=fallback_used,
    )


@app.post('/interview/report', response_model=InterviewReportResponse)
async def interview_report(payload: InterviewReportRequest):
    report, score, fallback_used, error = interview_service.generate_report(payload.transcript)
    if error:
        raise HTTPException(status_code=503, detail={'code': 'ai_unavailable', 'message': error})
    return InterviewReportResponse(report=report, score=score, fallback_used=fallback_used)


@app.post('/interview/tests/generate', response_model=InterviewTestGenerateResponse)
async def interview_tests_generate(payload: InterviewTestGenerateRequest):
    questions, fallback_used, error = interview_service.generate_test_questions(
        title=payload.title,
        topic=payload.topic,
        subtype=payload.subtype,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
        context=payload.context,
    )
    if error:
        raise HTTPException(status_code=503, detail={'code': 'ai_unavailable', 'message': error})
    return InterviewTestGenerateResponse(questions=questions, fallback_used=fallback_used, error=error)


@app.post('/vision/analyze-frame', response_model=VisionAnalyzeFrameResponse)
async def vision_analyze_frame(payload: VisionAnalyzeFrameRequest):
    metrics, risk_signals, fallback_used, error = video_analyzer_service.analyze_frame(payload.frame_base64, payload.telemetry)
    return VisionAnalyzeFrameResponse(metrics=metrics, risk_signals=risk_signals, fallback_used=fallback_used, error=error)


@app.post('/speech/stt', response_model=SpeechSTTResponse)
async def speech_stt(payload: SpeechSTTRequest):
    text, fallback_used, _error = stt_service.transcribe(payload.audio_base64)
    return SpeechSTTResponse(text=text, fallback_used=fallback_used)


@app.post('/speech/tts', response_model=SpeechTTSResponse)
async def speech_tts(payload: SpeechTTSRequest):
    audio_base64, fallback_used, _error = tts_service.synthesize(payload.text)
    return SpeechTTSResponse(audio_base64=audio_base64, voice_available=audio_base64 is not None, fallback_used=fallback_used)


@app.get('/speech/diagnostics', response_model=SpeechDiagnosticsResponse)
async def speech_diagnostics():
    return SpeechDiagnosticsResponse(
        stt_loaded=stt_service.available,
        stt_error=stt_service.load_error,
        tts_loaded=tts_service.available,
        tts_error=tts_service.load_error,
    )


@app.get('/metrics')
async def metrics():
    return Response(content=metrics_payload(), media_type=metrics_content_type())
