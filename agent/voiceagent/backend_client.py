"""
Async HTTP client for reporting call data back to the FastAPI backend.

Every public method is fire-and-forget safe — errors are logged but never
bubble up to crash the voice pipeline.  A simple retry loop handles transient
network blips.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("voiceagent.backend_client")

_MAX_RETRIES = 3
_RETRY_BACKOFF = 0.5  # seconds between retries (linear)
_REQUEST_TIMEOUT = 10.0  # seconds


class BackendClient:
    """Thin async wrapper around the internal backend REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-Internal-Key": api_key},
            timeout=httpx.Timeout(_REQUEST_TIMEOUT),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with automatic retries on transient errors."""
        import asyncio

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await self._client.request(
                    method, path, json=json, params=params
                )
                resp.raise_for_status()
                return resp
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF * attempt
                    log.warning(
                        "Backend %s %s attempt %d failed (%s), retrying in %.1fs",
                        method,
                        path,
                        attempt,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    log.error(
                        "Backend %s %s failed after %d attempts: %s",
                        method,
                        path,
                        _MAX_RETRIES,
                        exc,
                    )
        # Should not be reached, but keeps mypy happy
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Fetch the agent configuration (system prompt, greeting, etc.)."""
        resp = await self._request("GET", f"/internal/agents/{agent_id}")
        return resp.json()

    async def report_started(self, call_id: str) -> None:
        """Notify the backend that the agent has joined and the call started."""
        try:
            await self._request("POST", f"/internal/calls/{call_id}/started")
            log.info("Reported call started: %s", call_id)
        except Exception:
            log.exception("Failed to report call started for %s", call_id)

    async def report_turns(self, call_id: str, turns: list[dict[str, Any]]) -> None:
        """Push one or more conversation turns to the backend."""
        try:
            await self._request(
                "POST", f"/internal/calls/{call_id}/turns", json=turns
            )
        except Exception:
            log.exception("Failed to report turns for %s", call_id)

    async def report_metrics(self, call_id: str, metrics: dict[str, Any]) -> None:
        """Push latency / performance metrics for a single turn."""
        try:
            await self._request(
                "POST", f"/internal/calls/{call_id}/metrics", json=metrics
            )
        except Exception:
            log.exception("Failed to report metrics for %s", call_id)

    async def report_whisper(self, call_id: str, whisper: dict[str, Any]) -> None:
        """Log an operator whisper event."""
        try:
            await self._request(
                "POST", f"/internal/calls/{call_id}/whispers", json=whisper
            )
        except Exception:
            log.exception("Failed to report whisper for %s", call_id)

    async def report_ended(self, call_id: str) -> None:
        """Notify the backend that the call has ended."""
        try:
            await self._request("POST", f"/internal/calls/{call_id}/ended")
            log.info("Reported call ended: %s", call_id)
        except Exception:
            log.exception("Failed to report call ended for %s", call_id)

    async def close(self) -> None:
        """Gracefully close the underlying HTTP transport."""
        await self._client.aclose()
