"""Deterministic compliance rules (pure functions, no LLM)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# "recorded" / "recording" must refer to the call
RECORDING_REGEX = re.compile(r"\brecord(?:ed|ing|s)?\b", re.IGNORECASE)


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for safe subtraction."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def check_recording_disclosure(
    turns: list[dict[str, Any]],
    call_started_at: datetime | None,
) -> dict[str, Any]:
    """Check that the agent informed the caller the call is being recorded within the first 30 seconds.

    Rule: The agent must say the call is being recorded within the first 30 seconds (from call start).
    Deterministic check based on turn timestamps.
    """
    if not call_started_at:
        return {
            "rule": "recording_disclosure_30s",
            "method": "deterministic",
            "status": "fail",
            "offending_line": None,
            "offending_turn_idx": None,
            "detail": "Call start timestamp missing; cannot verify 30-second window.",
        }

    norm_call_start = _to_naive_utc(call_started_at)

    for turn in turns:
        if turn.get("speaker") != "agent":
            continue

        turn_start = turn.get("started_at")
        if not turn_start:
            continue

        norm_turn_start = _to_naive_utc(turn_start)

        # Calculate offset in seconds from call start
        delta_sec = (norm_turn_start - norm_call_start).total_seconds()

        # If turn started within the 30-second window (0 <= t <= 30)
        if 0.0 <= delta_sec <= 30.0:
            text = turn.get("text", "")
            if RECORDING_REGEX.search(text):
                return {
                    "rule": "recording_disclosure_30s",
                    "method": "deterministic",
                    "status": "pass",
                    "offending_line": None,
                    "offending_turn_idx": turn.get("idx"),
                    "detail": f"Agent mentioned recording at {delta_sec:.1f}s (turn {turn.get('idx')}): \"{text[:60]}...\"",
                }

        # If turn started beyond 30 seconds, subsequent turns will also be > 30s
        if delta_sec > 30.0:
            # Check if this turn mentions recording (late disclosure)
            text = turn.get("text", "")
            if RECORDING_REGEX.search(text):
                return {
                    "rule": "recording_disclosure_30s",
                    "method": "deterministic",
                    "status": "fail",
                    "offending_line": text,
                    "offending_turn_idx": turn.get("idx"),
                    "detail": f"Recording disclosure occurred late at {delta_sec:.1f}s (> 30s limit).",
                }

    return {
        "rule": "recording_disclosure_30s",
        "method": "deterministic",
        "status": "fail",
        "offending_line": None,
        "offending_turn_idx": None,
        "detail": "Agent never stated that the call was being recorded within the first 30 seconds.",
    }


def check_no_operator_mention(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Check that the agent never mentions the operator, supervisor, or whisper instructions."""
    FORBIDDEN_REGEX = re.compile(
        r"\b(?:operator|supervisor|whisper|whispered|instruction from supervisor|private note)\b",
        re.IGNORECASE,
    )

    for turn in turns:
        if turn.get("speaker") != "agent":
            continue
        text = turn.get("text", "")
        m = FORBIDDEN_REGEX.search(text)
        if m:
            return {
                "rule": "no_operator_mention",
                "method": "deterministic",
                "status": "fail",
                "offending_line": text,
                "offending_turn_idx": turn.get("idx"),
                "detail": f"Agent mentioned forbidden term '{m.group(0)}' in turn {turn.get('idx')}.",
            }

    return {
        "rule": "no_operator_mention",
        "method": "deterministic",
        "status": "pass",
        "offending_line": None,
        "offending_turn_idx": None,
        "detail": "Agent maintained secret supervisor protocol; no operator mentioned.",
    }
