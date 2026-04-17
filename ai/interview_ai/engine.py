import json

from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import get_settings

settings = get_settings()


class InterviewAIService:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.interview_llm_model_id
        self._tokenizer = None
        self._model = None
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    @property
    def available(self) -> bool:
        if self.is_loaded:
            return True
        if self._load_error is not None:
            return False
        self._load_model()
        return self.is_loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _load_model(self) -> None:
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                local_files_only=settings.hf_local_files_only,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.float32,
                device_map=None,
                low_cpu_mem_usage=True,
                local_files_only=settings.hf_local_files_only,
            )
            self._model.to('cpu')
            self._model.eval()
        except Exception as exc:
            self._load_error = f'{type(exc).__name__}: {exc}'
            self._model = None
            self._tokenizer = None

    def respond(self, history: list[dict], mode: str = 'text') -> tuple[str, bool, str | None]:
        if self.available:
            try:
                return self._respond_llm(history, mode), False, None
            except Exception as exc:
                return '', False, f'Interview model failure: {exc}'
        return '', False, self._load_error or 'Interview model unavailable'

    def generate_report(self, transcript: list[dict]) -> tuple[dict[str, Any], float | None, bool, str | None]:
        if self.available:
            try:
                report = self._report_llm(transcript)
                score = report.get('score')
                if isinstance(score, (float, int)):
                    score = float(score)
                return report, score, False, None
            except Exception as exc:
                return {}, None, False, f'Report generation failure: {exc}'

        return {}, None, False, self._load_error or 'Interview model unavailable'

    def generate_test_questions(
        self,
        *,
        title: str,
        topic: str,
        subtype: str,
        difficulty: int,
        question_count: int,
        context: dict,
    ) -> tuple[list[dict[str, Any]], bool, str | None]:
        if self.available:
            try:
                return (
                    self._test_generation_llm(
                        title=title,
                        topic=topic,
                        subtype=subtype,
                        difficulty=difficulty,
                        question_count=question_count,
                        context=context,
                    ),
                    False,
                    None,
                )
            except Exception as exc:
                return [], False, str(exc)

        return [], False, self._load_error or 'Interview model unavailable'

    def _respond_llm(self, history: list[dict], mode: str) -> str:
        system = (
            'You are a professional AI interviewer for software hiring. '
            'Ask one concise question at a time, follow up based on candidate answers, '
            'and keep tone respectful and neutral. Avoid disallowed topics.'
        )
        transcript = '\n'.join(f"{item.get('sender', 'unknown')}: {item.get('content', '')}" for item in history[-20:])
        prompt = (
            f'SYSTEM:\n{system}\n\n'
            f'INTERVIEW MODE: {mode}\n'
            f'CONVERSATION:\n{transcript}\n\n'
            'Return only interviewer next message:'
        )

        encoded = self._tokenizer(prompt, return_tensors='pt').to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **encoded,
                max_new_tokens=180,
                do_sample=True,
                top_p=0.9,
                temperature=0.7,
                eos_token_id=self._tokenizer.eos_token_id,
            )
        text = self._tokenizer.decode(output[0], skip_special_tokens=True)
        if 'Return only interviewer next message:' in text:
            text = text.split('Return only interviewer next message:')[-1].strip()
        return text[:1200]

    def _report_llm(self, transcript: list[dict]) -> dict[str, Any]:
        dialog = '\n'.join(f"{item.get('sender')}: {item.get('content')}" for item in transcript[-80:])
        prompt = (
            'Analyze interview transcript and return ONLY JSON with keys: '
            'strengths (array of strings), weaknesses (array of strings), '
            'score (number 0-100), summary (string), recommendation (string).\n\n'
            f'Transcript:\n{dialog}\n\nJSON:'
        )
        encoded = self._tokenizer(prompt, return_tensors='pt').to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **encoded,
                max_new_tokens=300,
                do_sample=False,
                temperature=0.1,
                eos_token_id=self._tokenizer.eos_token_id,
            )
        text = self._tokenizer.decode(output[0], skip_special_tokens=True)
        parsed = json.loads(self._extract_json(text))
        score = parsed.get('score')
        if not isinstance(score, (int, float)):
            raise ValueError('Interview report payload has no numeric score')
        return parsed

    def _test_generation_llm(
        self,
        *,
        title: str,
        topic: str,
        subtype: str,
        difficulty: int,
        question_count: int,
        context: dict,
    ) -> list[dict[str, Any]]:
        prompt = (
            'You are generating a technical hiring test. Return ONLY JSON object with key "questions" as array. '
            'Each question item must include: '
            'question_text (string), question_type (single_choice|multi_choice|text), '
            'options_json (array of {value,label}), correct_answer_json (object with key value), '
            'explanation (string), points (integer), metadata_json (object).\n\n'
            f'Title: {title}\n'
            f'Topic: {topic}\n'
            f'Subtype: {subtype}\n'
            f'Difficulty: {difficulty}\n'
            f'Question count: {question_count}\n'
            f'Context: {json.dumps(context)}\n\n'
            'JSON:'
        )

        encoded = self._tokenizer(prompt, return_tensors='pt').to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **encoded,
                max_new_tokens=1400,
                do_sample=True,
                temperature=0.4,
                top_p=0.92,
                eos_token_id=self._tokenizer.eos_token_id,
            )

        text = self._tokenizer.decode(output[0], skip_special_tokens=True)
        parsed = json.loads(self._extract_json(text))
        questions = parsed.get('questions') if isinstance(parsed, dict) else None
        if not isinstance(questions, list):
            raise ValueError('Invalid AI test generation payload')

        cleaned: list[dict[str, Any]] = []
        for question in questions[:question_count]:
            question_text = str(question.get('question_text', '')).strip()
            if not question_text:
                continue
            cleaned.append(
                {
                    'question_text': question_text,
                    'question_type': str(question.get('question_type', 'single_choice')),
                    'options_json': question.get('options_json', []),
                    'correct_answer_json': question.get('correct_answer_json', {}),
                    'explanation': question.get('explanation'),
                    'points': int(question.get('points', 1) or 1),
                    'metadata_json': question.get('metadata_json', {'topic': topic, 'subtype': subtype}),
                }
            )

        if not cleaned:
            raise ValueError('AI generated no usable test questions')

        return cleaned

    @staticmethod
    def _extract_json(text: str) -> str:
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or start >= end:
            raise ValueError('No JSON object found')
        return text[start : end + 1]
