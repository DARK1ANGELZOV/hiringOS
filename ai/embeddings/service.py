from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.embedding_model_id
        self._model: SentenceTransformer | None = None
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def available(self) -> bool:
        if self.is_loaded:
            return True
        if self._load_error is not None:
            return False
        try:
            self._model = SentenceTransformer(
                self.model_id,
                local_files_only=settings.hf_local_files_only,
            )
            return True
        except Exception as exc:
            self._load_error = f'{type(exc).__name__}: {exc}'
            return False

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def vectorize(self, text: str) -> list[float]:
        if not text.strip():
            return [0.0] * 384

        if not self.available:
            # Deterministic fallback vector.
            base = [float((ord(ch) % 31) / 31.0) for ch in text[:384]]
            return base + [0.0] * (384 - len(base))

        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()
