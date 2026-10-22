"""
Latency metric extraction helpers.

Converts the ``MetricsReport`` dictionary attached to each
``ChatMessage`` into a normalised dict of millisecond-valued fields
suitable for backend reporting and dashboard display.
"""

from __future__ import annotations

from typing import Any


def compute_turn_metrics(msg_metrics: dict[str, Any], turn_idx: int) -> dict[str, Any]:
    """Extract the 5-stage latency breakdown from a MetricsReport.

    The stages correspond to:

    1. **transcription_delay** — time from end-of-speech to STT result.
    2. **end_of_turn_delay** — time from STT result to accepted end-of-turn.
    3. **llm_ttft** — LLM time-to-first-token.
    4. **tts_ttfb** — TTS time-to-first-byte of audio.
    5. **e2e** — overall end-to-end latency (user stops speaking → agent
       audio begins playing).

    All values are converted from seconds to milliseconds and rounded to
    two decimal places.

    Parameters
    ----------
    msg_metrics:
        The raw ``MetricsReport`` dict from ``ChatMessage.metrics``.
    turn_idx:
        The conversation turn index for correlation.

    Returns
    -------
    dict
        A flat dictionary ready for JSON serialisation and backend
        ``POST /internal/calls/{id}/metrics``.
    """

    def _ms(key: str) -> float:
        """Safely convert a seconds-valued metric to milliseconds."""
        val = msg_metrics.get(key)
        if val is None:
            return 0.0
        try:
            return round(float(val) * 1000, 2)
        except (TypeError, ValueError):
            return 0.0

    return {
        "turn_idx": turn_idx,
        "transcription_delay_ms": _ms("transcription_delay"),
        "end_of_turn_delay_ms": _ms("end_of_turn_delay"),
        "llm_ttft_ms": _ms("llm_node_ttft"),
        "tts_ttfb_ms": _ms("tts_node_ttfb"),
        "e2e_ms": _ms("e2e_latency"),
    }
