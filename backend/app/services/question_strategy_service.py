from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from app.models.enums import InterviewQuestionType, InterviewStage


@dataclass
class QuestionStrategyService:
    """Deterministic interview question generator with adaptive follow-up logic."""

    def build_intro_questions(self, *, session_id: str, candidate_name: str, vacancy_title: str) -> list[dict[str, Any]]:
        base_questions = [
            f"What motivates you to apply for the {vacancy_title} role?",
            f"Describe your most relevant experience for {vacancy_title}.",
            "What do you expect from the team, processes, and ownership boundaries?",
        ]
        return [
            {
                'stage': InterviewStage.INTRO,
                'order_index': idx,
                'question_text': text,
                'question_type': InterviewQuestionType.TEXT,
                'expected_difficulty': 1,
                'metadata_json': {
                    'seed': self._seed(session_id, 'intro', idx),
                    'adaptive': True,
                    'target_signal': 'motivation_and_context',
                    'candidate_name': candidate_name,
                },
            }
            for idx, text in enumerate(base_questions, start=1)
        ]

    def build_theory_questions(self, *, session_id: str, stack: list[str], level: str) -> list[dict[str, Any]]:
        normalized_stack = stack[:3] if stack else ['software architecture', 'backend', 'testing']
        questions: list[dict[str, Any]] = []

        for idx, skill in enumerate(normalized_stack, start=1):
            questions.append(
                {
                    'stage': InterviewStage.THEORY,
                    'order_index': idx,
                    'question_text': (
                        f"Explain trade-offs when using {skill} at {level} level: "
                        'performance, reliability, maintainability, and observability.'
                    ),
                    'question_type': InterviewQuestionType.TEXT,
                    'expected_difficulty': min(5, 2 + idx),
                    'metadata_json': {
                        'seed': self._seed(session_id, 'theory', idx),
                        'skill': skill,
                        'level': level,
                        'expected_keywords': [skill, 'trade-off', 'latency', 'failure', 'monitoring'],
                    },
                }
            )

        return questions

    def build_ide_tasks(self, *, session_id: str, stack: list[str], level: str) -> list[dict[str, Any]]:
        primary = (stack[0] if stack else 'python').lower()

        if 'python' in primary or 'fastapi' in primary:
            return [
                {
                    'task_title': 'Reliable REST Endpoint',
                    'task_description': (
                        'Implement an endpoint with idempotency guarantees, validation, and resilient '
                        'error handling. Add unit tests for edge cases.'
                    ),
                    'starter_code': (
                        'def solve(payload: dict) -> dict:\n'
                        '    # TODO: implement\n'
                        '    raise NotImplementedError\n'
                    ),
                    'tests_json': [
                        {'name': 'validation', 'input': {'id': None}, 'expected': {'error': 'invalid'}},
                        {'name': 'idempotency', 'input': {'id': 'abc'}, 'expected': {'status': 'ok'}},
                    ],
                    'constraints_json': {'time_limit_s': 900, 'memory_mb': 512},
                    'expected_output_json': {'status': 'ok', 'id': 'abc'},
                    'difficulty': 3 if level.lower() in {'junior', 'middle'} else 4,
                    'metadata_json': {'seed': self._seed(session_id, 'ide', 1), 'format': 'backend_task'},
                },
                {
                    'task_title': 'Debug Concurrent Worker',
                    'task_description': 'Fix a race condition in async processing and explain root cause.',
                    'starter_code': (
                        'counter = 0\n\n'
                        'def run(items):\n'
                        '    global counter\n'
                        '    for _ in items:\n'
                        '        counter += 1\n'
                        '    return counter\n'
                    ),
                    'tests_json': [{'name': 'thread_safety', 'expected': 'deterministic'}],
                    'constraints_json': {'time_limit_s': 1200, 'memory_mb': 512},
                    'expected_output_json': {'thread_safe': True},
                    'difficulty': 4,
                    'metadata_json': {'seed': self._seed(session_id, 'ide', 2), 'format': 'debugging_task'},
                },
            ]

        return [
            {
                'task_title': 'Algorithmic Task',
                'task_description': 'Implement a function with O(n) complexity and cover edge cases.',
                'starter_code': 'function solve(items) {\n  // TODO\n}\n',
                'tests_json': [
                    {'name': 'base', 'input': [1, 2, 3], 'expected': 6},
                    {'name': 'edge', 'input': [], 'expected': 0},
                ],
                'constraints_json': {'time_limit_s': 900, 'memory_mb': 256},
                'expected_output_json': {'result': 6},
                'difficulty': 3,
                'metadata_json': {'seed': self._seed(session_id, 'ide', 1), 'format': 'algorithm_task'},
            }
        ]

    def should_add_follow_up(self, *, quick_score: float | None, response_time_ms: int | None, difficulty: int) -> bool:
        if quick_score is None:
            return False
        if quick_score < 0.45:
            return True
        if response_time_ms is not None and response_time_ms < 15000 and difficulty >= 4:
            return True
        return False

    def build_follow_up_question(self, *, session_id: str, stage: InterviewStage, order_index: int, base_question: str) -> dict[str, Any]:
        return {
            'stage': stage,
            'order_index': order_index,
            'question_text': (
                f"Follow-up: {base_question} Please provide a concrete example with metrics and constraints."
            ),
            'question_type': InterviewQuestionType.FOLLOW_UP,
            'expected_difficulty': 2,
            'metadata_json': {
                'seed': self._seed(session_id, f'{stage.value}_follow_up', order_index),
                'adaptive_reason': 'low_confidence_or_suspicious_speed',
            },
        }

    @staticmethod
    def _seed(session_id: str, scope: str, index: int) -> str:
        return sha256(f'{session_id}:{scope}:{index}'.encode('utf-8')).hexdigest()[:12]
