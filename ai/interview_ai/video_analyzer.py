import base64
import io
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.core.config import get_settings

settings = get_settings()


class VideoAnalyzerService:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.video_analysis_model_id
        self._processor = None
        self._model = None
        self._load_error: str | None = None
        self._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    @property
    def is_loaded(self) -> bool:
        return self._processor is not None and self._model is not None

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
            self._processor = CLIPProcessor.from_pretrained(
                self.model_id,
                local_files_only=settings.hf_local_files_only,
            )
            self._model = CLIPModel.from_pretrained(
                self.model_id,
                local_files_only=settings.hf_local_files_only,
            )
        except Exception as exc:
            self._load_error = f'{type(exc).__name__}: {exc}'
            self._processor = None
            self._model = None

    def analyze_frame(self, frame_base64: str, telemetry: dict | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], bool, str | None]:
        telemetry = telemetry or {}

        try:
            frame = self._decode_image(frame_base64)
        except Exception as exc:
            return {}, [{'signal_type': 'video_decode_error', 'severity': 'high', 'details': {'error': str(exc)}}], True, str(exc)

        metrics = self._frame_metrics(frame, telemetry)
        risk_signals = self._derive_risk_signals(metrics, telemetry)

        if self.available:
            try:
                clip_scores = self._clip_scene_scores(frame)
                metrics['clip_scores'] = clip_scores
                if clip_scores.get('person_looking_away', 0.0) >= 0.4:
                    risk_signals.append(
                        {
                            'signal_type': 'video_looking_away',
                            'severity': 'medium',
                            'details': {'confidence': clip_scores.get('person_looking_away')},
                        }
                    )
                if clip_scores.get('multiple_people', 0.0) >= 0.35:
                    risk_signals.append(
                        {
                            'signal_type': 'video_multiple_people',
                            'severity': 'high',
                            'details': {'confidence': clip_scores.get('multiple_people')},
                        }
                    )
                return metrics, risk_signals, False, None
            except Exception as exc:
                return metrics, risk_signals, True, f'CLIP analysis fallback: {exc}'

        return metrics, risk_signals, True, self._load_error or 'Video model unavailable'

    @staticmethod
    def _decode_image(frame_base64: str) -> np.ndarray:
        clean_value = frame_base64
        if ',' in clean_value and clean_value.strip().startswith('data:'):
            clean_value = clean_value.split(',', 1)[1]
        raw = base64.b64decode(clean_value)
        image = Image.open(io.BytesIO(raw)).convert('RGB')
        return np.array(image)

    def _frame_metrics(self, frame: np.ndarray, telemetry: dict) -> dict[str, Any]:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))

        faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        face_count = int(len(faces))

        return {
            'frame_width': int(frame.shape[1]),
            'frame_height': int(frame.shape[0]),
            'blur_score': round(blur_score, 4),
            'brightness': round(brightness, 4),
            'face_count': face_count,
            'tab_visible': bool(telemetry.get('tab_visible', True)),
            'noise_level': round(float(np.std(gray)), 4),
        }

    def _clip_scene_scores(self, frame: np.ndarray) -> dict[str, float]:
        if self._processor is None or self._model is None:
            return {}

        image = Image.fromarray(frame)
        prompts = [
            'a person looking at the camera during an interview',
            'a person looking away from camera while typing',
            'multiple people in front of a laptop',
            'an empty chair and no person visible',
        ]

        inputs = self._processor(text=prompts, images=image, return_tensors='pt', padding=True)
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits_per_image = outputs.logits_per_image
            probabilities = logits_per_image.softmax(dim=1).cpu().numpy().tolist()[0]

        return {
            'person_looking_at_camera': round(float(probabilities[0]), 4),
            'person_looking_away': round(float(probabilities[1]), 4),
            'multiple_people': round(float(probabilities[2]), 4),
            'no_person': round(float(probabilities[3]), 4),
        }

    @staticmethod
    def _derive_risk_signals(metrics: dict[str, Any], telemetry: dict) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        face_count = int(metrics.get('face_count', 0))
        if face_count == 0:
            signals.append({'signal_type': 'video_no_face', 'severity': 'high', 'details': {'face_count': 0}})
        elif face_count > 1:
            signals.append({'signal_type': 'video_multiple_faces', 'severity': 'high', 'details': {'face_count': face_count}})

        blur_score = float(metrics.get('blur_score', 0.0))
        if blur_score < 20.0:
            signals.append({'signal_type': 'video_blur', 'severity': 'medium', 'details': {'blur_score': blur_score}})

        brightness = float(metrics.get('brightness', 0.0))
        if brightness < 25.0:
            signals.append({'signal_type': 'video_dark_frame', 'severity': 'low', 'details': {'brightness': brightness}})

        if telemetry.get('tab_visible') is False:
            signals.append({'signal_type': 'video_tab_hidden', 'severity': 'medium', 'details': {'tab_visible': False}})

        if telemetry.get('camera_disabled') is True:
            signals.append({'signal_type': 'camera_disabled', 'severity': 'high', 'details': {'camera_disabled': True}})

        return signals
