"""
Configuration for the LiveKit voice-agent worker.

All values can be overridden via environment variables or a ``.env`` file
placed next to the worker process (automatically loaded by *pydantic-settings*).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Voice-agent worker settings — sourced from env vars / .env."""

    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "agent/.env"],
        extra="ignore",
    )

    # ---- Backend communication ----
    backend_url: str = "http://localhost:8000"
    internal_api_key: str = "dev-internal-key"

    # ---- LiveKit agent identity ----
    agent_name: str = "support-agent"

    # ---- LLM (Groq, OpenAI-compatible) ----
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""  # Set via GROQ_API_KEY or LLM_API_KEY env var
    groq_api_key: str = ""
    llm_model: str = "qwen/qwen3.8-27b"
    max_reply_tokens: int = 120
    llm_temperature: float = 0.3

    # ---- STT (Deepgram) ----
    stt_model: str = "nova-3"
    deepgram_api_key: str = ""

    # ---- TTS (Deepgram) ----
    tts_voice: str = "aura-2-thalia-en"
    tts_speed: float = 0.92

    # ---- Turn detection / endpointing ----
    use_turn_detector: bool = True
    min_endpointing_delay: float = 0.2
    max_endpointing_delay: float = 1.8
