import json
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import get_settings

settings = get_settings()


class ResumeParserService:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.resume_llm_model_id
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
            self._tokenizer = None
            self._model = None

    def parse(self, text: str) -> tuple[dict[str, Any], bool, str | None]:
        normalized = (text or '')[: settings.max_resume_chars]
        if not normalized.strip():
            return {}, True, 'Empty resume text'

        if self.available:
            try:
                structured = self._llm_parse(normalized)
                return structured, False, None
            except Exception as exc:
                return {}, True, f'LLM parse failed: {exc}'

        return {}, True, self._load_error or 'Resume model unavailable'

    def _llm_parse(self, text: str) -> dict[str, Any]:
        system = (
            'Extract resume information and return ONLY valid JSON. '
            'Schema: {"full_name": string|null, "contacts": {"email": string|null, "phone": string|null, "linkedin": string|null, "github": string|null}, '
            '"skills": [{"name": string, "level": string|null}], '
            '"experience": [{"company": string|null, "title": string|null, "start": string|null, "end": string|null, "description": string|null}], '
            '"education": [{"institution": string|null, "degree": string|null, "field": string|null, "start": string|null, "end": string|null}], '
            '"projects": [{"name": string|null, "description": string|null, "tech": [string]}], '
            '"languages": [{"name": string, "level": string|null}]}. '
            'Never include markdown.'
        )
        prompt = f'SYSTEM:\n{system}\n\nRESUME:\n{text}\n\nJSON:'

        encoded = self._tokenizer(prompt, return_tensors='pt').to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **encoded,
                max_new_tokens=512,
                do_sample=False,
                temperature=0.1,
                eos_token_id=self._tokenizer.eos_token_id,
            )
        completion = self._tokenizer.decode(output[0], skip_special_tokens=True)
        extracted = self._extract_json(completion)
        parsed = json.loads(extracted)
        if not isinstance(parsed, dict):
            raise ValueError('LLM parser returned invalid JSON payload')
        return parsed

    @staticmethod
    def _extract_json(text: str) -> str:
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            raise ValueError('JSON block was not found in model output')
        return text[start : end + 1]
