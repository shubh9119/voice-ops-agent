"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings loaded from environment variables.

    All fields map to env vars in UPPER_SNAKE_CASE by default.
    Example: ``livekit_api_key`` -> ``LIVEKIT_API_KEY``
    """

    # Database
    database_url: str = "sqlite+aiosqlite:///./voiceops.db"

    # LiveKit connectivity
    livekit_url: str = "ws://localhost:7880"
    livekit_public_url: str = "ws://localhost:7880"
    livekit_api_key: str = "APInKAhvt3yFR9G"
    livekit_api_secret: str = "aBc1dEf2gHi3jKl4mNo5pQr6sTu7vWx8yZ90ABCD"

    # Agent worker identity
    agent_name: str = "support-agent"

    # Auth keys
    internal_api_key: str = "dev-internal-key"   # agent-worker -> backend
    operator_api_key: str = "dev-operator-key"   # operator dashboard

    # LLM provider keys
    openai_api_key: str = ""
    llm_api_key: str = ""
    groq_api_key: str = ""
    llm_compliance_model: str = "gpt-4o-mini"

    model_config = {
        "env_file": [".env", "../.env", "backend/.env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Module-level singleton
settings = Settings()


def get_settings() -> Settings:
    """Return the global Settings instance."""
    return settings
