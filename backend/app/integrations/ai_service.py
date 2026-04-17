import base64
from collections.abc import Sequence
from time import perf_counter

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.core.metrics import AI_CLIENT_LATENCY_SECONDS

settings = get_settings()


class AIServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.ai_service_url.rstrip('/')

    async def _observe_request(self, operation: str, coro):
        started = perf_counter()
        try:
            result = await coro
            AI_CLIENT_LATENCY_SECONDS.labels(operation=operation, status='success').observe(perf_counter() - started)
            return result
        except Exception:
            AI_CLIENT_LATENCY_SECONDS.labels(operation=operation, status='error').observe(perf_counter() - started)
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def parse_resume(self, *, file_name: str, file_content: bytes) -> dict:
        files = {'file': (file_name, file_content, 'application/octet-stream')}

        async def _call():
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f'{self.base_url}/resume/parse', files=files)
                response.raise_for_status()
                return response.json()

        return await self._observe_request('parse_resume', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def parse_resume_text(self, *, text: str) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f'{self.base_url}/resume/parse-text', json={'text': text})
                response.raise_for_status()
                return response.json()

        return await self._observe_request('parse_resume_text', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def embedding(self, *, text: str) -> list[float]:
        async def _call():
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(f'{self.base_url}/embeddings/vectorize', json={'text': text})
                response.raise_for_status()
                payload = response.json()
                return payload['embedding']

        return await self._observe_request('embedding', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def interview_reply(self, *, history: Sequence[dict], mode: str) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f'{self.base_url}/interview/respond',
                    json={'history': list(history), 'mode': mode},
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('interview_reply', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def interview_report(self, *, transcript: Sequence[dict]) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f'{self.base_url}/interview/report',
                    json={'transcript': list(transcript)},
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('interview_report', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def generate_test_questions(
        self,
        *,
        title: str,
        topic: str,
        subtype: str,
        difficulty: int,
        question_count: int,
        context: dict,
    ) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(
                    f'{self.base_url}/interview/tests/generate',
                    json={
                        'title': title,
                        'topic': topic,
                        'subtype': subtype,
                        'difficulty': difficulty,
                        'question_count': question_count,
                        'context': context,
                    },
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('generate_test_questions', _call())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def video_analyze_frame(self, *, frame_base64: str, telemetry: dict) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f'{self.base_url}/vision/analyze-frame',
                    json={'frame_base64': frame_base64, 'telemetry': telemetry},
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('video_analyze_frame', _call())

    async def speech_to_text(self, *, audio_base64: str) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(
                    f'{self.base_url}/speech/stt',
                    json={'audio_base64': audio_base64},
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('speech_to_text', _call())

    async def text_to_speech(self, *, text: str) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(
                    f'{self.base_url}/speech/tts',
                    json={'text': text},
                )
                response.raise_for_status()
                return response.json()

        return await self._observe_request('text_to_speech', _call())

    async def speech_diagnostics(self) -> dict:
        async def _call():
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(f'{self.base_url}/speech/diagnostics')
                response.raise_for_status()
                return response.json()

        return await self._observe_request('speech_diagnostics', _call())


ai_client = AIServiceClient()


def audio_bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')
