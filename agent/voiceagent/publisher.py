"""
LiveKit data-channel publisher.

Sends live transcript deltas, agent state changes, and other real-time
events to all browser participants in the room.
"""

from __future__ import annotations

import json
import logging
import time

from livekit import rtc

log = logging.getLogger("voiceagent.publisher")


class Publisher:
    """Publishes structured JSON messages over LiveKit data channels."""

    def __init__(self, room: rtc.Room) -> None:
        self._room = room

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _publish(self, topic: str, payload: dict, *, reliable: bool = True) -> None:
        """Serialize and publish a JSON payload to the given topic."""
        try:
            await self._room.local_participant.publish_data(
                payload=json.dumps(payload).encode("utf-8"),
                topic=topic,
                reliable=reliable,
            )
        except Exception:
            log.exception("Failed to publish data on topic=%s", topic)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_transcript(
        self,
        turn_idx: int,
        speaker: str,
        text: str,
        is_final: bool,
        interrupted: bool = False,
    ) -> None:
        """Send a transcript update (interim or final) to all browser viewers.

        Parameters
        ----------
        turn_idx:
            Monotonically increasing turn counter for this call.
        speaker:
            ``"user"`` or ``"agent"``.
        text:
            The (partial or complete) transcription text.
        is_final:
            ``True`` when this is the final version of the transcript for this
            turn; ``False`` for interim / streaming updates.
        interrupted:
            ``True`` if the agent was interrupted mid-sentence and the text
            has been trimmed to what was actually spoken.
        """
        await self._publish(
            "transcript",
            {
                "type": "transcript",
                "turn_idx": turn_idx,
                "speaker": speaker,
                "text": text,
                "is_final": is_final,
                "interrupted": interrupted,
                "timestamp": time.time(),
            },
        )

    async def send_agent_state(self, state: str) -> None:
        """Broadcast an agent state change to browsers.

        Parameters
        ----------
        state:
            One of ``"listening"``, ``"thinking"``, ``"speaking"``,
            ``"takeover"``, ``"idle"``.
        """
        await self._publish(
            "agent_state",
            {
                "type": "agent_state",
                "state": state,
                "timestamp": time.time(),
            },
        )

    async def send_whisper_ack(self, whisper_text: str) -> None:
        """Acknowledge receipt of an operator whisper."""
        await self._publish(
            "whisper_ack",
            {
                "type": "whisper_ack",
                "text": whisper_text,
                "timestamp": time.time(),
            },
        )
