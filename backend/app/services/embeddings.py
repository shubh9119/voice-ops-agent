"""Embedding service wrapping Google Gemini text-embedding-004."""

import asyncio
import hashlib
from typing import Optional

from app.config import get_settings

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class EmbeddingService:
    """Wrapper around Google Generative AI Embeddings.

    Provides both sync and async embedding generation.
    Underlying model (text-embedding-004) produces 768-dim vectors.
    """

    _instance: Optional["EmbeddingService"] = None

    def __init__(self):
        self.dimension = get_settings().EMBEDDING_DIMENSION
        self.reinit()

    def reinit(self, api_key: Optional[str] = None):
        """Reinitialize with current or updated API key."""
        settings = get_settings()
        key = api_key or settings.GOOGLE_API_KEY

        is_test_key = (
            not key
            or key.startswith("test-")
            or key.startswith("mock-")
            or key == "your-google-api-key-here"
        )

        if HAS_GENAI and not is_test_key:
            try:
                model_name = settings.EMBEDDING_MODEL.replace("models/", "")
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=model_name,
                    google_api_key=key,
                )
            except Exception:
                self.embeddings = None
        else:
            self.embeddings = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def _fallback_vector(self, text: str) -> list[float]:
        """Deterministic 768-dim vector for testing/fallback."""
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        return [int(h[i % len(h)], 16) / 15.0 for i in range(self.dimension)]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.embeddings:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.embeddings.embed_documents, texts
                )
            except Exception:
                pass
        return [self._fallback_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        if self.embeddings:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.embeddings.embed_query, text
                )
            except Exception:
                pass
        return self._fallback_vector(text)
