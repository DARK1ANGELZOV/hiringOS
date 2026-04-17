import asyncio
import base64
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.metrics import ANTI_CHEAT_SIGNALS_TOTAL, REPORT_GENERATION_EVENTS_TOTAL
from app.integrations.ai_service import ai_client
from app.integrations.minio_storage import get_minio_storage
from app.models.enums import AnalysisStatus, AntiCheatSeverity, InterviewStatus
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.anti_cheat_service import AntiCheatService
from app.services.interview_state_machine import InterviewStateMachine
from app.services.notification_service import NotificationService
from app.services.scoring_engine_service import ScoringEngineService

MAX_RETRIES = 3


async def _track_task(
    *,
    repository: InterviewRepository,
    session_id: UUID,
    task_id: str,
    task_name: str,
    status: str,
    retries: int = 0,
    error_message: str | None = None,
) -> None:
    await repository.upsert_task_status(
        session_id=session_id,
        task_id=task_id,
        task_name=task_name,
        status=status,
        retries=retries,
        error_message=error_message,
    )


async def _retry_or_fail(self, *, repository: InterviewRepository, session_id: UUID, task_name: str, exc: Exception):
    retries = int(self.request.retries)
    task_id = str(self.request.id)

    if retries < MAX_RETRIES:
        await _track_task(
            repository=repository,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status='retrying',
            retries=retries + 1,
            error_message=str(exc),
        )
        await repository.create_event(
            session_id=session_id,
            event_type='worker_retry_scheduled',
            payload_json={'task_name': task_name, 'retries': retries + 1, 'error': str(exc)},
        )
        await repository.db.commit()
        raise self.retry(exc=exc, countdown=min(30, 2 ** retries))

    await _track_task(
        repository=repository,
        session_id=session_id,
        task_id=task_id,
        task_name=task_name,
        status='failed',
        retries=retries,
        error_message=str(exc),
    )
    await repository.create_event(
        session_id=session_id,
        event_type='report_failed' if task_name == 'interview.generate_report' else 'ai_analysis_failed',
        payload_json={'task_name': task_name, 'error': str(exc)},
    )
    await repository.db.commit()


@celery_app.task(name='interview.analyze_answer', bind=True)
def analyze_answer(self, answer_id: str):
    asyncio.run(_analyze_answer(self, answer_id))


async def _analyze_answer(self, answer_id: str):
    async with SessionLocal() as db:
        repository = InterviewRepository(db)

        answer = await repository.get_answer(UUID(answer_id))
        if not answer:
            return

        task_name = 'interview.analyze_answer'
        session_id = answer.session_id
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            if answer.analysis_status == AnalysisStatus.READY and answer.ai_summary:
                await _track_task(
                    repository=repository,
                    session_id=session_id,
                    task_id=task_id,
                    task_name=task_name,
                    status='skipped',
                )
                await db.commit()
                return

            question = await repository.get_question(answer.question_id)
            prompt_question = question.question_text if question else 'No question provided'
            transcript = [
                {'sender': 'interviewer', 'content': prompt_question},
                {'sender': 'candidate', 'content': answer.answer_text or ''},
            ]

            analysis_payload = await ai_client.interview_report(transcript=transcript)
            report_data = analysis_payload.get('report', {}) if isinstance(analysis_payload, dict) else {}
            summary = report_data.get('summary') if isinstance(report_data, dict) else None

            if not summary:
                raise ValueError('AI analysis returned empty summary')

            answer.ai_summary = summary
            answer.analysis_status = AnalysisStatus.READY

            await repository.create_event(
                session_id=session_id,
                event_type='ai_analysis_completed',
                payload_json={'answer_id': str(answer.id), 'summary_available': bool(summary)},
            )

            # Trigger embedding calculation as independent asynchronous step.
            embedding_task = celery_app.send_task('interview.calculate_answer_embedding', args=[str(answer.id)])
            await repository.upsert_task_status(
                session_id=session_id,
                task_id=embedding_task.id,
                task_name='interview.calculate_answer_embedding',
                status='queued',
            )

            await _track_task(
                repository=repository,
                session_id=session_id,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            answer.analysis_status = AnalysisStatus.PARTIAL
            await _retry_or_fail(self, repository=repository, session_id=session_id, task_name=task_name, exc=exc)


@celery_app.task(name='interview.transcribe_answer_audio', bind=True)
def transcribe_answer_audio(self, answer_id: str):
    asyncio.run(_transcribe_answer_audio(self, answer_id))


async def _transcribe_answer_audio(self, answer_id: str):
    async with SessionLocal() as db:
        repository = InterviewRepository(db)

        answer = await repository.get_answer(UUID(answer_id))
        if not answer:
            return

        session_id = answer.session_id
        task_name = 'interview.transcribe_answer_audio'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            if not answer.answer_audio_file_id:
                await _track_task(
                    repository=repository,
                    session_id=session_id,
                    task_id=task_id,
                    task_name=task_name,
                    status='skipped',
                )
                await db.commit()
                return

            artifact = await repository.get_media_artifact(answer.answer_audio_file_id)
            if not artifact:
                raise ValueError('Audio artifact not found')

            storage = get_minio_storage()
            audio_bytes = storage.get_file(artifact.object_key)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            stt_payload = await ai_client.speech_to_text(audio_base64=audio_base64)
            text = stt_payload.get('text') if isinstance(stt_payload, dict) else None

            if text:
                answer.answer_text = text
                if answer.analysis_status != AnalysisStatus.READY:
                    answer.analysis_status = AnalysisStatus.PARTIAL

            await repository.create_event(
                session_id=session_id,
                event_type='voice_transcription_completed',
                payload_json={'answer_id': str(answer.id), 'text_available': bool(text)},
            )

            await _track_task(
                repository=repository,
                session_id=session_id,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_id, task_name=task_name, exc=exc)


@celery_app.task(name='interview.generate_question_tts', bind=True)
def generate_question_tts(self, session_id: str, question_id: str):
    asyncio.run(_generate_question_tts(self, session_id, question_id))


async def _generate_question_tts(self, session_id: str, question_id: str):
    async with SessionLocal() as db:
        repository = InterviewRepository(db)
        session_uuid = UUID(session_id)
        task_name = 'interview.generate_question_tts'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_uuid,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            question = await repository.get_question(UUID(question_id))
            if not question:
                raise ValueError('Question not found')

            tts_payload = await ai_client.text_to_speech(text=question.question_text)
            audio_base64 = tts_payload.get('audio_base64') if isinstance(tts_payload, dict) else None

            if audio_base64:
                raw_audio = base64.b64decode(audio_base64)
                storage = get_minio_storage()
                bucket, object_key = storage.upload_file(
                    filename=f'question_tts_{question.id}.wav',
                    data=raw_audio,
                    content_type='audio/wav',
                )
                await repository.create_media_artifact(
                    session_id=session_uuid,
                    bucket=bucket,
                    object_key=object_key,
                    content_type='audio/wav',
                    size_bytes=len(raw_audio),
                )

            await repository.create_event(
                session_id=session_uuid,
                event_type='question_tts_generated',
                payload_json={'question_id': question_id, 'audio_available': bool(audio_base64)},
            )

            await _track_task(
                repository=repository,
                session_id=session_uuid,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_uuid, task_name=task_name, exc=exc)


@celery_app.task(name='interview.analyze_video_frame', bind=True)
def analyze_video_frame(self, session_id: str, artifact_id: str, telemetry: dict | None = None):
    asyncio.run(_analyze_video_frame(self, session_id, artifact_id, telemetry or {}))


async def _analyze_video_frame(self, session_id: str, artifact_id: str, telemetry: dict):
    session_uuid = UUID(session_id)
    artifact_uuid = UUID(artifact_id)

    async with SessionLocal() as db:
        repository = InterviewRepository(db)
        anti_cheat = AntiCheatService(repository)
        task_name = 'interview.analyze_video_frame'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_uuid,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            artifact = await repository.get_media_artifact(artifact_uuid)
            if not artifact:
                raise ValueError('Video frame artifact not found')

            storage = get_minio_storage()
            frame_bytes = storage.get_file(artifact.object_key)
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

            result = await ai_client.video_analyze_frame(frame_base64=frame_base64, telemetry=telemetry)
            metrics = result.get('metrics', {}) if isinstance(result, dict) else {}
            risk_signals = result.get('risk_signals', []) if isinstance(result, dict) else []
            fallback_used = bool(result.get('fallback_used', False)) if isinstance(result, dict) else True

            for signal in risk_signals:
                signal_type = str(signal.get('signal_type', 'video_anomaly'))
                severity_raw = str(signal.get('severity', 'medium')).lower()
                if severity_raw == 'critical':
                    severity = AntiCheatSeverity.CRITICAL
                elif severity_raw == 'high':
                    severity = AntiCheatSeverity.HIGH
                elif severity_raw == 'low':
                    severity = AntiCheatSeverity.LOW
                else:
                    severity = AntiCheatSeverity.MEDIUM

                await anti_cheat.collect_signal(
                    session_id=session_uuid,
                    signal_type=signal_type,
                    severity=severity,
                    value_json={'artifact_id': artifact_id, 'details': signal.get('details', {}), 'metrics': metrics},
                )
                ANTI_CHEAT_SIGNALS_TOTAL.labels(severity=severity.value).inc()

            if risk_signals:
                aggregate_task = celery_app.send_task('interview.aggregate_anti_cheat', args=[session_id])
                await repository.upsert_task_status(
                    session_id=session_uuid,
                    task_id=aggregate_task.id,
                    task_name='interview.aggregate_anti_cheat',
                    status='queued',
                )

            await repository.create_event(
                session_id=session_uuid,
                event_type='video_frame_analyzed',
                payload_json={
                    'artifact_id': artifact_id,
                    'metrics': metrics,
                    'signals': risk_signals,
                    'fallback_used': fallback_used,
                },
            )

            await _track_task(
                repository=repository,
                session_id=session_uuid,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_uuid, task_name=task_name, exc=exc)


@celery_app.task(name='interview.check_plagiarism', bind=True)
def check_plagiarism(self, submission_id: str):
    asyncio.run(_check_plagiarism(self, submission_id))


async def _check_plagiarism(self, submission_id: str):
    async with SessionLocal() as db:
        repository = InterviewRepository(db)
        scoring = ScoringEngineService()

        submission = await repository.get_ide_submission(UUID(submission_id))
        if not submission:
            return

        task = await repository.get_ide_task(submission.task_id)
        if not task:
            return

        session_id = task.session_id
        task_name = 'interview.check_plagiarism'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            similarity = scoring.plagiarism_similarity(
                candidate_code=submission.code_text,
                baseline_code=task.starter_code,
            )
            submission.plagiarism_score = similarity

            if similarity >= 0.92:
                anti_cheat = AntiCheatService(repository)
                await anti_cheat.collect_signal(
                    session_id=session_id,
                    signal_type='plagiarism',
                    severity=AntiCheatSeverity.HIGH,
                    value_json={'submission_id': str(submission.id), 'similarity': similarity},
                )

            await repository.create_event(
                session_id=session_id,
                event_type='plagiarism_checked',
                payload_json={'submission_id': str(submission.id), 'similarity': similarity},
            )

            await _track_task(
                repository=repository,
                session_id=session_id,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_id, task_name=task_name, exc=exc)


@celery_app.task(name='interview.aggregate_anti_cheat', bind=True)
def aggregate_anti_cheat(self, session_id: str):
    asyncio.run(_aggregate_anti_cheat(self, session_id))


async def _aggregate_anti_cheat(self, session_id: str):
    session_uuid = UUID(session_id)
    async with SessionLocal() as db:
        repository = InterviewRepository(db)
        anti_cheat = AntiCheatService(repository)

        task_name = 'interview.aggregate_anti_cheat'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_uuid,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            score, risk = await anti_cheat.aggregate_signals(session_uuid)
            await repository.create_event(
                session_id=session_uuid,
                event_type='anti_cheat_aggregated',
                payload_json={'score': score, 'risk_level': risk.value},
            )

            await _track_task(
                repository=repository,
                session_id=session_uuid,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_uuid, task_name=task_name, exc=exc)


@celery_app.task(name='interview.calculate_answer_embedding', bind=True)
def calculate_answer_embedding(self, answer_id: str):
    asyncio.run(_calculate_answer_embedding(self, answer_id))


async def _calculate_answer_embedding(self, answer_id: str):
    async with SessionLocal() as db:
        repository = InterviewRepository(db)

        answer = await repository.get_answer(UUID(answer_id))
        if not answer:
            return

        session_id = answer.session_id
        task_name = 'interview.calculate_answer_embedding'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_id,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            if not answer.answer_text:
                await _track_task(
                    repository=repository,
                    session_id=session_id,
                    task_id=task_id,
                    task_name=task_name,
                    status='skipped',
                )
                await db.commit()
                return

            embedding = await ai_client.embedding(text=answer.answer_text)
            payload = dict(answer.answer_json or {})
            payload['embedding_preview'] = embedding[:16]
            payload['embedding_dims'] = len(embedding)
            answer.answer_json = payload

            await repository.create_event(
                session_id=session_id,
                event_type='embedding_calculated',
                payload_json={'answer_id': str(answer.id), 'dims': len(embedding)},
            )

            await _track_task(
                repository=repository,
                session_id=session_id,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            await db.commit()
        except Exception as exc:
            await _retry_or_fail(self, repository=repository, session_id=session_id, task_name=task_name, exc=exc)


@celery_app.task(name='interview.generate_report', bind=True)
def generate_report(self, session_id: str):
    asyncio.run(_generate_report(self, session_id))


async def _generate_report(self, session_id: str):
    session_uuid = UUID(session_id)

    async with SessionLocal() as db:
        repository = InterviewRepository(db)
        candidate_repository = CandidateRepository(db)
        notification_service = NotificationService(NotificationRepository(db))
        anti_cheat = AntiCheatService(repository)
        scoring = ScoringEngineService()

        session = await repository.get_session(session_uuid)
        if not session:
            return

        task_name = 'interview.generate_report'
        task_id = str(self.request.id)

        await _track_task(
            repository=repository,
            session_id=session_uuid,
            task_id=task_id,
            task_name=task_name,
            status='started',
            retries=int(self.request.retries),
        )

        try:
            assessment = await repository.latest_assessment(session_uuid)
            if assessment and assessment.generation_status == AnalysisStatus.READY and session.status == InterviewStatus.COMPLETED:
                await _track_task(
                    repository=repository,
                    session_id=session_uuid,
                    task_id=task_id,
                    task_name=task_name,
                    status='skipped',
                )
                await db.commit()
                return

            answers = await repository.list_answers(session_uuid)
            ide_submissions = await repository.list_ide_submissions(session_uuid)

            question_map = {}
            for answer in answers:
                question = await repository.get_question(answer.question_id)
                if question:
                    question_map[str(question.id)] = question

            transcript: list[dict] = []
            intro_scores: list[float] = []
            theory_scores: list[float] = []
            communication_scores: list[float] = []

            for answer in answers:
                question = question_map.get(str(answer.question_id))
                question_text = question.question_text if question else 'Question unavailable'
                stage = question.stage.value if question else 'unknown'
                quick = float(answer.quick_score or 0.0)

                if stage == 'intro':
                    intro_scores.append(quick)
                elif stage == 'theory':
                    theory_scores.append(quick)

                words = len((answer.answer_text or '').split())
                communication_scores.append(min(words / 80.0, 1.0))

                transcript.append({'sender': 'interviewer', 'content': question_text})
                transcript.append({'sender': 'candidate', 'content': answer.answer_text or ''})

            code_scores: list[float] = []
            plagiarism_alert = False
            for submission in ide_submissions:
                tests_ratio = (submission.execution_result_json or {}).get('tests_passed_ratio')
                code_score = scoring.quick_code_score(code=submission.code_text, tests_passed_ratio=tests_ratio)
                plagiarism = submission.plagiarism_score or 0.0
                if plagiarism >= 0.92:
                    plagiarism_alert = True
                code_scores.append(max(0.0, code_score - plagiarism * 0.5))

            hard = scoring.aggregate_stage_score(theory_scores)
            soft = scoring.aggregate_stage_score(intro_scores)
            communication = scoring.aggregate_stage_score(communication_scores)
            problem_solving = scoring.aggregate_stage_score(theory_scores + code_scores)
            code_quality = scoring.aggregate_stage_score(code_scores)
            business_thinking = scoring.aggregate_stage_score(intro_scores + theory_scores[:1])

            category_values = [hard, soft, communication, problem_solving, code_quality, business_thinking]
            score_total = round((sum(category_values) / max(len(category_values), 1)) * 100.0, 2)

            report_payload = await ai_client.interview_report(transcript=transcript)
            llm_report = report_payload.get('report', {}) if isinstance(report_payload, dict) else {}

            summary_text = llm_report.get('summary') if isinstance(llm_report, dict) else None
            if not summary_text:
                raise ValueError('AI report summary is unavailable')

            recommendation = llm_report.get('recommendation') if isinstance(llm_report, dict) else 'reserve'
            strengths = llm_report.get('strengths') if isinstance(llm_report, dict) else []
            weaknesses = llm_report.get('weaknesses') if isinstance(llm_report, dict) else []

            risk_flags = await anti_cheat.evaluate_risk(session_uuid)
            anti_cheat_score, anti_cheat_level = await anti_cheat.aggregate_signals(session_uuid)

            if plagiarism_alert:
                risk_flags.append({'signal_type': 'plagiarism', 'severity': 'high', 'details': {'reason': 'high_similarity'}})

            if anti_cheat_level.value in {'high', 'critical'}:
                recommendation = 'repeat_interview'

            enriched = {
                'summary': summary_text,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendation': recommendation,
                'anti_cheat': {'score': anti_cheat_score, 'level': anti_cheat_level.value},
            }

            assessment = await repository.upsert_assessment(
                session_id=session_uuid,
                ai_model_name='local-llm',
                defaults={
                    'raw_result_json': enriched,
                    'summary_text': summary_text,
                    'score_total': score_total,
                    'score_hard_skills': round(hard * 100.0, 2),
                    'score_soft_skills': round(soft * 100.0, 2),
                    'score_communication': round(communication * 100.0, 2),
                    'score_problem_solving': round(problem_solving * 100.0, 2),
                    'score_code_quality': round(code_quality * 100.0, 2),
                    'score_business_thinking': round(business_thinking * 100.0, 2),
                    'risk_flags_json': risk_flags,
                    'recommendations_json': [
                        {'type': 'hiring_recommendation', 'value': recommendation},
                        {'type': 'anti_cheat_level', 'value': anti_cheat_level.value},
                    ],
                    'generation_status': AnalysisStatus.READY,
                },
            )

            session.analysis_status = AnalysisStatus.READY
            if session.status == InterviewStatus.AWAITING_AI_ANALYSIS:
                state_machine = InterviewStateMachine(session.status)
                session.status = state_machine.complete()

            await repository.create_event(
                session_id=session_uuid,
                event_type='ai_analysis_completed',
                payload_json={'assessment_id': str(assessment.id), 'task_id': task_id},
            )
            await repository.create_event(
                session_id=session_uuid,
                event_type='report_ready',
                payload_json={'assessment_id': str(assessment.id)},
            )

            if session.interviewer_id:
                await notification_service.create(
                    user_id=session.interviewer_id,
                    title='Interview report is ready',
                    message='AI interview report was generated and is ready for review.',
                    entity_type='interview',
                    entity_id=str(session.id),
                )

            candidate = await candidate_repository.get_by_id(session.candidate_id)
            if candidate and candidate.owner_user_id:
                await notification_service.create(
                    user_id=candidate.owner_user_id,
                    title='Interview completed',
                    message='Your interview is completed. HR will review the report soon.',
                    entity_type='interview',
                    entity_id=str(session.id),
                )

            await _track_task(
                repository=repository,
                session_id=session_uuid,
                task_id=task_id,
                task_name=task_name,
                status='completed',
            )
            REPORT_GENERATION_EVENTS_TOTAL.labels(result='ready').inc()
            await db.commit()
        except Exception as exc:
            session.analysis_status = AnalysisStatus.PARTIAL
            if session.status == InterviewStatus.AWAITING_AI_ANALYSIS:
                session.status = InterviewStatus.COMPLETED

            await repository.upsert_assessment(
                session_id=session_uuid,
                ai_model_name='local-llm',
                defaults={
                    'raw_result_json': {},
                    'summary_text': 'Report generated in degraded mode due to AI worker error.',
                    'generation_status': AnalysisStatus.PARTIAL,
                },
            )
            REPORT_GENERATION_EVENTS_TOTAL.labels(result='partial').inc()

            await _retry_or_fail(self, repository=repository, session_id=session_uuid, task_name=task_name, exc=exc)
