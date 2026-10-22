"""
Call recorder — subscribes to AgentSession events and streams
conversation turns, latency metrics, and interim transcripts to the
FastAPI backend and to browser viewers via the data-channel publisher.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from livekit.agents import AgentSession

from .backend_client import BackendClient
from .latency import compute_turn_metrics
from .publisher import Publisher

log = logging.getLogger("voiceagent.recorder")


def _safe_task(coro: Any) -> asyncio.Task:
    """Create a task with exception logging so fire-and-forget calls
    don't silently swallow errors."""
    task = asyncio.create_task(coro)
    task.add_done_callback(_log_task_exception)
    return task


def _log_task_exception(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        log.error("Background recorder task failed: %s", exc, exc_info=exc)


class CallRecorder:
    """Records conversation events from an ``AgentSession``.

    Parameters
    ----------
    call_id:
        Unique identifier for the ongoing call.
    backend:
        :class:`BackendClient` instance used to push data to the REST API.
    publisher:
        :class:`Publisher` instance used to push live transcripts to browsers.
    """

    def __init__(
        self,
        call_id: str,
        backend: BackendClient,
        publisher: Publisher,
    ) -> None:
        self.call_id = call_id
        self._backend = backend
        self._pub = publisher
        self._turn_idx: int = 0
        self._pending_turns: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def attach(self, session: AgentSession) -> None:
        """Subscribe to relevant events on the given session.

        Must be called **before** ``session.start()`` so that no events
        are missed.
        """

        @session.on("conversation_item_added")
        def _on_item(event: Any) -> None:
            item = event.item if hasattr(event, "item") else event

            # Skip function-call items that lack a text role
            role = getattr(item, "role", None)
            if role is None:
                return

            # ---- Build turn record ----
            metrics: dict[str, Any] = {}
            if hasattr(item, "metrics") and item.metrics:
                metrics = dict(item.metrics) if not isinstance(item.metrics, dict) else item.metrics

            now = time.time()
            started_at_ts = metrics.get("started_speaking_at") or getattr(item, "created_at", now)
            stopped_at_ts = metrics.get("stopped_speaking_at")

            turn: dict[str, Any] = {
                "idx": self._turn_idx,
                "speaker": "agent" if role == "assistant" else "user",
                "text": getattr(item, "text_content", "") or "",
                "started_at": datetime.fromtimestamp(
                    float(started_at_ts), tz=timezone.utc
                ).isoformat(),
                "ended_at": (
                    datetime.fromtimestamp(
                        float(stopped_at_ts), tz=timezone.utc
                    ).isoformat()
                    if stopped_at_ts
                    else None
                ),
                "interrupted": getattr(item, "interrupted", False),
            }
            current_idx = self._turn_idx
            self._turn_idx += 1

            # ---- Fire-and-forget: push turn to backend ----
            _safe_task(self._backend.report_turns(self.call_id, [turn]))

            # ---- Fire-and-forget: publish final transcript to browsers ----
            _safe_task(
                self._pub.send_transcript(
                    turn_idx=current_idx,
                    speaker=turn["speaker"],
                    text=turn["text"],
                    is_final=True,
                    interrupted=turn["interrupted"],
                )
            )

            # ---- If assistant turn, extract and report latency metrics ----
            if role == "assistant" and metrics:
                latency = compute_turn_metrics(metrics, current_idx)
                _safe_task(self._backend.report_metrics(self.call_id, latency))

        @session.on("user_input_transcribed")
        def _on_interim(event: Any) -> None:
            is_final = getattr(event, "is_final", False)
            transcript = getattr(event, "transcript", "")

            if not is_final and transcript:
                # Publish interim (streaming) transcript for live display
                _safe_task(
                    self._pub.send_transcript(
                        turn_idx=self._turn_idx,
                        speaker="user",
                        text=transcript,
                        is_final=False,
                    )
                )

        log.info("CallRecorder attached to session for call %s", self.call_id)
