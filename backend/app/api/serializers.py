from app.schemas.admin import AuditLogResponse
from app.schemas.candidate import CandidateResponse, CandidateStatusHistoryResponse
from app.schemas.document import DocumentResponse
from app.schemas.feedback import FeedbackResponse
from app.schemas.interview import (
    AntiCheatSignalResponse,
    IdeSubmissionResponse,
    IdeTaskResponse,
    InterviewEventResponse,
    InterviewQuestionResponse,
    InterviewRequestResponse,
    InterviewSessionResponse,
)
from app.schemas.notification import NotificationResponse
from app.schemas.resume import ResumeProfileResponse
from app.schemas.tests import (
    InterviewQuestionBankResponse,
    KnowledgeTestAnswerResponse,
    KnowledgeTestAttemptResponse,
    KnowledgeTestDetailResponse,
    KnowledgeTestQuestionResponse,
    KnowledgeTestResponse,
)
from app.schemas.profile_option import ProfileOptionResponse
from app.schemas.vacancy import VacancyApplicationResponse, VacancyCandidateViewResponse, VacancyMatchInfo, VacancyResponse


def candidate_to_schema(candidate) -> CandidateResponse:
    return CandidateResponse(
        id=candidate.id,
        organization_id=candidate.organization_id,
        owner_user_id=candidate.owner_user_id,
        created_by_user_id=candidate.created_by_user_id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        date_of_birth=candidate.date_of_birth,
        city=candidate.city,
        location=candidate.location,
        citizenship=candidate.citizenship,
        linkedin_url=candidate.linkedin_url,
        github_url=candidate.github_url,
        portfolio_url=candidate.portfolio_url,
        desired_position=candidate.desired_position,
        specialization=candidate.specialization,
        level=candidate.level,
        headline=candidate.headline,
        summary=candidate.summary,
        salary_expectation=candidate.salary_expectation,
        employment_type=candidate.employment_type,
        work_format=candidate.work_format,
        work_schedule=candidate.work_schedule,
        relocation_ready=candidate.relocation_ready,
        travel_ready=candidate.travel_ready,
        status=candidate.status,
        skills_raw=candidate.skills_raw,
        competencies_raw=candidate.competencies_raw,
        languages_raw=candidate.languages_raw,
        skills=candidate.skills,
        experience=candidate.experience,
        education=candidate.education,
        projects=candidate.projects,
        languages=candidate.languages,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def candidate_status_history_to_schema(item) -> CandidateStatusHistoryResponse:
    return CandidateStatusHistoryResponse(
        id=item.id,
        candidate_id=item.candidate_id,
        previous_status=item.previous_status,
        new_status=item.new_status,
        changed_by_user_id=item.changed_by_user_id,
        comment=item.comment,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
    )


def document_to_schema(document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        candidate_id=document.candidate_id,
        bucket=document.bucket,
        object_key=document.object_key,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        document_type=document.document_type,
        created_at=document.created_at,
    )


def resume_to_schema(profile) -> ResumeProfileResponse:
    return ResumeProfileResponse(
        id=profile.id,
        candidate_id=profile.candidate_id,
        document_id=profile.document_id,
        parser_status=profile.parser_status,
        parser_error=profile.parser_error,
        structured_data=profile.structured_data,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def interview_to_schema(session) -> InterviewSessionResponse:
    return InterviewSessionResponse(
        id=session.id,
        candidate_id=session.candidate_id,
        vacancy_id=session.vacancy_id,
        interviewer_id=session.interviewer_id,
        status=session.status,
        mode=session.mode,
        current_stage=session.current_stage,
        started_at=session.started_at,
        finished_at=session.finished_at,
        scheduled_at=session.scheduled_at,
        interview_format=session.interview_format,
        meeting_link=session.meeting_link,
        meeting_location=session.meeting_location,
        scheduling_comment=session.scheduling_comment,
        requested_by_manager_id=session.requested_by_manager_id,
        candidate_invite_status=session.candidate_invite_status,
        manager_invite_status=session.manager_invite_status,
        confirmed_candidate_at=session.confirmed_candidate_at,
        confirmed_manager_at=session.confirmed_manager_at,
        analysis_status=session.analysis_status,
        anti_cheat_score=session.anti_cheat_score,
        anti_cheat_level=session.anti_cheat_level,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def interview_request_to_schema(item) -> InterviewRequestResponse:
    return InterviewRequestResponse(
        id=item.id,
        candidate_id=item.candidate_id,
        vacancy_id=item.vacancy_id,
        manager_user_id=item.manager_user_id,
        hr_user_id=item.hr_user_id,
        requested_mode=item.requested_mode,
        requested_format=item.requested_format,
        requested_time=item.requested_time,
        comment=item.comment,
        status=item.status,
        review_comment=item.review_comment,
        reviewed_at=item.reviewed_at,
        created_interview_session_id=item.created_interview_session_id,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def interview_question_to_schema(question) -> InterviewQuestionResponse:
    return InterviewQuestionResponse(
        id=question.id,
        session_id=question.session_id,
        stage=question.stage,
        order_index=question.order_index,
        question_text=question.question_text,
        question_type=question.question_type,
        expected_difficulty=question.expected_difficulty,
        metadata_json=question.metadata_json,
        created_at=question.created_at,
    )


def interview_event_to_schema(event) -> InterviewEventResponse:
    return InterviewEventResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type,
        payload_json=event.payload_json,
        created_at=event.created_at,
    )


def ide_task_to_schema(task) -> IdeTaskResponse:
    return IdeTaskResponse(
        id=task.id,
        session_id=task.session_id,
        task_title=task.task_title,
        task_description=task.task_description,
        starter_code=task.starter_code,
        tests_json=task.tests_json,
        constraints_json=task.constraints_json,
        expected_output_json=task.expected_output_json,
        difficulty=task.difficulty,
        created_at=task.created_at,
    )


def ide_submission_to_schema(submission) -> IdeSubmissionResponse:
    return IdeSubmissionResponse(
        id=submission.id,
        task_id=submission.task_id,
        plagiarism_score=submission.plagiarism_score,
        behavior_score=submission.behavior_score,
        submitted_at=submission.submitted_at,
    )


def anti_cheat_signal_to_schema(signal) -> AntiCheatSignalResponse:
    return AntiCheatSignalResponse(
        id=signal.id,
        signal_type=signal.signal_type,
        severity=signal.severity,
        value_json=signal.value_json,
        created_at=signal.created_at,
    )


def feedback_to_schema(feedback) -> FeedbackResponse:
    return FeedbackResponse(
        id=feedback.id,
        session_id=feedback.session_id,
        hr_user_id=feedback.hr_user_id,
        manager_user_id=feedback.manager_user_id,
        overall_rating=feedback.overall_rating,
        strengths=feedback.strengths,
        weaknesses=feedback.weaknesses,
        recommendation=feedback.recommendation,
        comments=feedback.comments,
        created_at=feedback.created_at,
    )


def notification_to_schema(notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        created_at=notification.created_at,
    )


def audit_to_schema(log) -> AuditLogResponse:
    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        metadata=log.metadata_json,
        created_at=log.created_at,
    )


def vacancy_to_schema(vacancy) -> VacancyResponse:
    return VacancyResponse(
        id=str(vacancy.id),
        title=vacancy.title,
        level=vacancy.level,
        department=vacancy.department,
        stack_json=vacancy.stack_json,
        description=vacancy.description,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def vacancy_candidate_view_to_schema(vacancy, *, match: dict | None = None) -> VacancyCandidateViewResponse:
    match_schema = None
    if match is not None:
        match_schema = VacancyMatchInfo(
            score_percent=float(match.get('score_percent', 0.0)),
            matched_skills=list(match.get('matched_skills', [])),
            missing_skills=list(match.get('missing_skills', [])),
        )
    return VacancyCandidateViewResponse(
        **vacancy_to_schema(vacancy).model_dump(),
        match=match_schema,
    )


def vacancy_application_to_schema(item) -> VacancyApplicationResponse:
    return VacancyApplicationResponse(
        id=str(item.id),
        vacancy_id=str(item.vacancy_id),
        candidate_id=str(item.candidate_id),
        created_by_user_id=str(item.created_by_user_id) if item.created_by_user_id else None,
        status=item.status.value if hasattr(item.status, 'value') else str(item.status),
        cover_letter_text=item.cover_letter_text,
        note=item.note,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def profile_option_to_schema(item) -> ProfileOptionResponse:
    return ProfileOptionResponse(
        id=str(item.id),
        option_type=item.option_type.value if hasattr(item.option_type, 'value') else str(item.option_type),
        value=item.value,
        created_by_user_id=str(item.created_by_user_id) if item.created_by_user_id else None,
        created_at=item.created_at,
    )


def knowledge_test_question_to_schema(question) -> KnowledgeTestQuestionResponse:
    return KnowledgeTestQuestionResponse(
        id=question.id,
        order_index=question.order_index,
        question_text=question.question_text,
        question_type=question.question_type,
        options_json=question.options_json,
        explanation=question.explanation,
        points=question.points,
        metadata_json=question.metadata_json,
    )


def knowledge_test_to_schema(item) -> KnowledgeTestResponse:
    return KnowledgeTestResponse(
        id=item.id,
        created_by_user_id=item.created_by_user_id,
        title=item.title,
        topic=item.topic,
        subtype=item.subtype,
        difficulty=item.difficulty,
        is_ai_generated=item.is_ai_generated,
        is_custom=item.is_custom,
        company_scope=item.company_scope,
        config_json=item.config_json,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def knowledge_test_detail_to_schema(item) -> KnowledgeTestDetailResponse:
    return KnowledgeTestDetailResponse(
        **knowledge_test_to_schema(item).model_dump(),
        questions=[knowledge_test_question_to_schema(question) for question in item.questions],
    )


def knowledge_test_attempt_to_schema(item) -> KnowledgeTestAttemptResponse:
    return KnowledgeTestAttemptResponse(
        id=item.id,
        test_id=item.test_id,
        candidate_id=item.candidate_id,
        session_id=item.session_id,
        status=item.status,
        score=item.score,
        max_score=item.max_score,
        started_at=item.started_at,
        finished_at=item.finished_at,
        analysis_json=item.analysis_json,
    )


def knowledge_test_answer_to_schema(item) -> KnowledgeTestAnswerResponse:
    return KnowledgeTestAnswerResponse(
        id=item.id,
        attempt_id=item.attempt_id,
        question_id=item.question_id,
        answer_json=item.answer_json,
        is_correct=item.is_correct,
        points_earned=item.points_earned,
        submitted_at=item.submitted_at,
    )


def question_bank_to_schema(item) -> InterviewQuestionBankResponse:
    return InterviewQuestionBankResponse(
        id=item.id,
        created_by_user_id=item.created_by_user_id,
        vacancy_id=item.vacancy_id,
        stage=item.stage.value,
        question_text=item.question_text,
        expected_difficulty=item.expected_difficulty,
        metadata_json=item.metadata_json,
        is_active=item.is_active,
        created_at=item.created_at,
    )
