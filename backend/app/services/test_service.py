from __future__ import annotations

from difflib import SequenceMatcher
from uuid import UUID

from fastapi import HTTPException, status

from app.integrations.ai_service import ai_client
from app.models.enums import InterviewStage, UserRole
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.test_repository import KnowledgeTestRepository
from app.schemas.tests import (
    InterviewQuestionBankCreateRequest,
    KnowledgeTestAnswerSubmitRequest,
    KnowledgeTestCreateRequest,
    KnowledgeTestGenerateRequest,
)


class KnowledgeTestService:
    def __init__(
        self,
        *,
        repository: KnowledgeTestRepository,
        interview_repository: InterviewRepository,
        candidate_repository: CandidateRepository,
    ):
        self.repository = repository
        self.interview_repository = interview_repository
        self.candidate_repository = candidate_repository

    async def create_custom_test(self, *, payload: KnowledgeTestCreateRequest, creator_user_id: UUID, creator_role: UserRole):
        self._assert_creator_role(creator_role)

        item = await self.repository.create_test(
            created_by_user_id=creator_user_id,
            title=payload.title,
            topic=payload.topic,
            subtype=payload.subtype,
            difficulty=payload.difficulty,
            is_ai_generated=False,
            is_custom=True,
            company_scope=payload.company_scope,
            config_json={'source': 'manual'},
        )

        questions_payload = []
        for idx, question in enumerate(payload.questions, start=1):
            questions_payload.append(
                {
                    'test_id': item.id,
                    'order_index': idx,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'options_json': question.options_json,
                    'correct_answer_json': question.correct_answer_json,
                    'explanation': question.explanation,
                    'points': question.points,
                    'metadata_json': question.metadata_json,
                }
            )

        if questions_payload:
            await self.repository.create_questions(questions_payload)

        return await self.repository.get_test(item.id)

    async def generate_test(self, *, payload: KnowledgeTestGenerateRequest, creator_user_id: UUID, creator_role: UserRole):
        self._assert_creator_role(creator_role)

        generated = await ai_client.generate_test_questions(
            title=payload.title,
            topic=payload.topic,
            subtype=payload.subtype,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            context=payload.context,
        )

        questions = generated.get('questions') if isinstance(generated, dict) else None
        if not isinstance(questions, list) or not questions:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='AI test generation returned empty result')

        item = await self.repository.create_test(
            created_by_user_id=creator_user_id,
            title=payload.title,
            topic=payload.topic,
            subtype=payload.subtype,
            difficulty=payload.difficulty,
            is_ai_generated=True,
            is_custom=False,
            company_scope=payload.company_scope,
            config_json={
                'source': 'ai_generated',
                'requested_question_count': payload.question_count,
                'context': payload.context,
            },
        )

        questions_payload = []
        for idx, question in enumerate(questions, start=1):
            question_text = str(question.get('question_text', '')).strip()
            if not question_text:
                continue
            questions_payload.append(
                {
                    'test_id': item.id,
                    'order_index': idx,
                    'question_text': question_text,
                    'question_type': str(question.get('question_type', 'single_choice')),
                    'options_json': question.get('options_json', []),
                    'correct_answer_json': question.get('correct_answer_json', {}),
                    'explanation': question.get('explanation'),
                    'points': int(question.get('points', 1) or 1),
                    'metadata_json': question.get('metadata_json', {}),
                }
            )

        if not questions_payload:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='AI generated invalid test questions')

        await self.repository.create_questions(questions_payload)
        return await self.repository.get_test(item.id)

    async def list_tests(self, *, topic: str | None = None, subtype: str | None = None, created_by_user_id: UUID | None = None):
        return await self.repository.list_tests(topic=topic, subtype=subtype, created_by_user_id=created_by_user_id)

    async def get_test(self, test_id: UUID):
        item = await self.repository.get_test(test_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Knowledge test not found')
        return item

    async def start_attempt(self, *, test_id: UUID, candidate_id: UUID, session_id: UUID | None):
        await self.get_test(test_id)
        return await self.repository.start_attempt(
            test_id=test_id,
            candidate_id=candidate_id,
            session_id=session_id,
            status='in_progress',
        )

    async def submit_answer(self, *, attempt_id: UUID, payload: KnowledgeTestAnswerSubmitRequest):
        attempt = await self.repository.get_attempt(attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Test attempt not found')
        if attempt.status != 'in_progress':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Attempt is already finished')

        question = await self.repository.get_question(payload.question_id)
        if not question or question.test_id != attempt.test_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found for attempt test')

        is_correct, points = self._evaluate_answer(payload.answer_json, question.correct_answer_json, question.points)
        return await self.repository.upsert_answer(
            attempt_id=attempt.id,
            question_id=question.id,
            answer_json=payload.answer_json,
            is_correct=is_correct,
            points_earned=points,
        )

    async def finish_attempt(self, *, attempt_id: UUID):
        attempt = await self.repository.get_attempt(attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Attempt not found')
        if attempt.status == 'completed':
            return attempt

        questions = await self.repository.list_questions(attempt.test_id)
        answers = await self.repository.list_attempt_answers(attempt.id)

        total_points = float(sum(item.points for item in questions))
        earned_points = float(sum(item.points_earned for item in answers))

        answered = len(answers)
        question_count = len(questions)
        completion_ratio = round((answered / question_count), 4) if question_count else 0.0
        score_percent = round((earned_points / total_points) * 100.0, 2) if total_points else 0.0

        analysis_json = {
            'answered': answered,
            'total_questions': question_count,
            'completion_ratio': completion_ratio,
            'score_percent': score_percent,
            'correct_answers': len([item for item in answers if item.is_correct is True]),
        }

        return await self.repository.finish_attempt(
            attempt,
            score=earned_points,
            max_score=total_points,
            analysis_json=analysis_json,
        )

    async def list_attempts(self, *, test_id: UUID | None = None, candidate_id: UUID | None = None):
        return await self.repository.list_attempts(test_id=test_id, candidate_id=candidate_id)

    async def create_question_bank_item(
        self,
        *,
        payload: InterviewQuestionBankCreateRequest,
        creator_user_id: UUID,
        creator_role: UserRole,
    ):
        self._assert_creator_role(creator_role)

        try:
            stage = InterviewStage(payload.stage)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid stage for question bank') from exc

        return await self.interview_repository.create_custom_question(
            created_by_user_id=creator_user_id,
            vacancy_id=payload.vacancy_id,
            stage=stage,
            question_text=payload.question_text,
            expected_difficulty=payload.expected_difficulty,
            metadata_json=payload.metadata_json,
            is_active=True,
        )

    async def list_question_bank(self, *, vacancy_id: UUID | None = None, stage: InterviewStage | None = None, creator_id: UUID | None = None):
        return await self.interview_repository.list_custom_questions(
            vacancy_id=vacancy_id,
            stage=stage,
            creator_id=creator_id,
            active_only=True,
            limit=300,
        )

    @staticmethod
    def _assert_creator_role(role: UserRole):
        if role not in {UserRole.ADMIN, UserRole.HR, UserRole.MANAGER}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only HR/Manager/Admin can manage tests')

    @staticmethod
    def _evaluate_answer(answer_json: dict, expected_json: dict, points: int) -> tuple[bool | None, float]:
        if not expected_json:
            return None, 0.0

        expected_value = expected_json.get('value')
        answer_value = answer_json.get('value')

        if isinstance(expected_value, list) and isinstance(answer_value, list):
            is_correct = sorted(str(x) for x in answer_value) == sorted(str(x) for x in expected_value)
            return is_correct, float(points if is_correct else 0)

        if isinstance(expected_value, str) and isinstance(answer_value, str):
            expected_normalized = expected_value.strip().lower()
            answer_normalized = answer_value.strip().lower()
            if not expected_normalized:
                return None, 0.0

            exact_match = answer_normalized == expected_normalized
            if exact_match:
                return True, float(points)

            similarity = SequenceMatcher(None, answer_normalized, expected_normalized).ratio()
            if similarity >= 0.85:
                return True, float(points)
            if similarity >= 0.65:
                return False, float(points * 0.5)
            return False, 0.0

        is_correct = answer_value == expected_value
        return bool(is_correct), float(points if is_correct else 0)
