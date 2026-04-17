import base64
import io

import numpy as np
import soundfile as sf
import torch
from datasets import load_dataset
from transformers import (
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
    SpeechT5Processor,
    pipeline,
)

from app.core.config import get_settings

settings = get_settings()


class STTService:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.stt_model_id
        self._pipeline = None
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def available(self) -> bool:
        if self.is_loaded:
            return True
        if self._load_error is not None:
            return False
        try:
            self._pipeline = pipeline(
                'automatic-speech-recognition',
                model=self.model_id,
                model_kwargs={'local_files_only': settings.hf_local_files_only},
            )
            return True
        except Exception as exc:
            self._load_error = f'{type(exc).__name__}: {exc}'
            return False

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def transcribe(self, audio_base64: str) -> tuple[str, bool, str | None]:
        if not self.available:
            return '', True, self._load_error or 'STT model unavailable'

        try:
            audio_bytes = base64.b64decode(audio_base64)
            data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            result = self._pipeline({'array': data, 'sampling_rate': sample_rate})
            text = result.get('text', '').strip()
            return text, False, None
        except Exception as exc:
            return '', True, f'STT fallback: {exc}'


class TTSService:
    def __init__(self):
        self._processor = None
        self._model = None
        self._vocoder = None
        self._speaker_embeddings = None
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return all([self._processor, self._model, self._vocoder, self._speaker_embeddings is not None])

    @property
    def available(self) -> bool:
        if self.is_loaded:
            return True
        if self._load_error is not None:
            return False
        self._load()
        return self.is_loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _load(self) -> None:
        try:
            self._processor = SpeechT5Processor.from_pretrained(
                settings.tts_model_id,
                local_files_only=settings.hf_local_files_only,
            )
            self._model = SpeechT5ForTextToSpeech.from_pretrained(
                settings.tts_model_id,
                local_files_only=settings.hf_local_files_only,
            )
            self._vocoder = SpeechT5HifiGan.from_pretrained(
                settings.tts_vocoder_model_id,
                local_files_only=settings.hf_local_files_only,
            )

            download_mode = 'reuse_cache_if_exists' if settings.hf_local_files_only else 'reuse_dataset_if_exists'
            dataset = load_dataset(
                settings.tts_speaker_dataset_id,
                split='validation',
                download_mode=download_mode,
            )
            idx = 0
            hint = settings.tts_female_speaker_hint.lower()
            for i, row in enumerate(dataset):
                filename = str(row.get('filename', '')).lower()
                if hint and hint in filename:
                    idx = i
                    break
            xvector = dataset[idx]['xvector']
            self._speaker_embeddings = torch.tensor(xvector).unsqueeze(0)
        except Exception as exc:
            self._load_error = f'{type(exc).__name__}: {exc}'
            self._processor = None
            self._model = None
            self._vocoder = None
            self._speaker_embeddings = None

    def synthesize(self, text: str) -> tuple[str | None, bool, str | None]:
        if not self.available:
            return None, True, self._load_error or 'TTS model unavailable'

        try:
            with torch.no_grad():
                inputs = self._processor(text=text, return_tensors='pt')
                speech = self._model.generate_speech(
                    inputs['input_ids'],
                    self._speaker_embeddings,
                    vocoder=self._vocoder,
                )
            speech_np = speech.cpu().numpy()
            buffer = io.BytesIO()
            sf.write(buffer, speech_np, samplerate=16000, format='WAV')
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return encoded, False, None
        except Exception as exc:
            return None, True, f'TTS fallback: {exc}'
