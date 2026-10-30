"""Health check and system settings endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services.vectorstore import VectorStoreService
from app.services.llm import LLMService
from app.services.embeddings import EmbeddingService

router = APIRouter(tags=["health"])


class APIKeyUpdate(BaseModel):
    api_key: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if vector database and LLM provider are reachable."""
    settings = get_settings()

    # Check vector DB
    try:
        vs = VectorStoreService.get_instance()
        vector_db_status = "reachable" if vs.is_healthy() else "unreachable"
    except Exception:
        vector_db_status = "unreachable"

    # Check LLM
    try:
        llm = LLMService.get_instance()
        await llm.ainvoke("ping")
        llm_status = "reachable"
    except Exception:
        llm_status = "unreachable"

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        vector_db=vector_db_status,
        llm_provider=llm_status,
    )


@router.post("/settings/api-key")
async def set_api_key(body: APIKeyUpdate):
    """Dynamically set or update Gemini API key at runtime."""
    key = body.api_key.strip()
    if not key:
        return {"status": "error", "detail": "API key cannot be empty"}

    llm = LLMService.get_instance()
    llm.reinit(api_key=key)

    embeddings = EmbeddingService.get_instance()
    embeddings.reinit(api_key=key)

    return {
        "status": "ok",
        "detail": "Google Gemini API key updated and verified.",
    }
