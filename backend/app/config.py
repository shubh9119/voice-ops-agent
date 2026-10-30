"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """All configuration read from env vars / .env file."""

    # --- App ---
    APP_NAME: str = "Omnibound Brand Q&A Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- LLM (Google Gemini) ---
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # --- Vector DB (ChromaDB) ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_PREFIX: str = "omnibound"

    # --- RAG ---
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    MAX_RETRIES: int = 1

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
