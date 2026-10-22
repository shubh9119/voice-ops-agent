"""Internal endpoints consumed by the agent worker.

All routes require the ``X-Internal-Key`` header to match
``settings.internal_api_key``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Agent, Call, Turn, TurnMetric, Whisper
from app.schemas import (
    AgentOut,
    TurnCreate,
    TurnMetricCreate,
    TurnMetricOut,
    TurnOut,
    WhisperCreate,
    WhisperOut,
)
from app.compliance.runner import run_compliance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def _verify_internal_key(
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
) -> None:
    """Reject requests that don't carry a valid internal API key."""
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/calls/{call_id}/started",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_verify_internal_key)],
)
async def mark_call_started(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Mark a call as active with the current UTC timestamp."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    call.status = "active"
    call.started_at = datetime.now(timezone.utc)
    await session.commit()
    logger.info("Call %s marked as active.", call_id)
    return {"ok": True}


@router.post(
    "/calls/{call_id}/turns",
    response_model=list[TurnOut],
    dependencies=[Depends(_verify_internal_key)],
)
async def upsert_turns(
    call_id: str,
    turns: list[TurnCreate],
    session: AsyncSession = Depends(get_session),
) -> list[Turn]:
    """Batch upsert transcript turns for a call.

    If a turn with the given ``idx`` already exists for this call it is
    updated; otherwise a new row is inserted.
    """
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    result_turns: list[Turn] = []

    for tc in turns:
        # Check for existing turn by call_id + idx
        existing = (
            await session.execute(
                select(Turn).where(
                    Turn.call_id == call_id, Turn.idx == tc.idx
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.speaker = tc.speaker
            existing.text = tc.text
            existing.started_at = tc.started_at
            existing.ended_at = tc.ended_at
            existing.interrupted = tc.interrupted
            result_turns.append(existing)
        else:
            turn = Turn(
                call_id=call_id,
                idx=tc.idx,
                speaker=tc.speaker,
                text=tc.text,
                started_at=tc.started_at,
                ended_at=tc.ended_at,
                interrupted=tc.interrupted,
            )
            session.add(turn)
            result_turns.append(turn)

    await session.commit()
    for t in result_turns:
        await session.refresh(t)
    logger.info("Upserted %d turns for call %s.", len(turns), call_id)
    return result_turns


@router.post(
    "/calls/{call_id}/metrics",
    response_model=TurnMetricOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_internal_key)],
)
async def save_metrics(
    call_id: str,
    body: TurnMetricCreate,
    session: AsyncSession = Depends(get_session),
) -> TurnMetric:
    """Save latency metrics for a single turn."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    metric = TurnMetric(call_id=call_id, **body.model_dump())
    session.add(metric)
    await session.commit()
    await session.refresh(metric)
    logger.info("Saved metrics for call %s turn %d.", call_id, body.turn_idx)
    return metric


@router.post(
    "/calls/{call_id}/whispers",
    response_model=WhisperOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_internal_key)],
)
async def log_whisper(
    call_id: str,
    body: WhisperCreate,
    session: AsyncSession = Depends(get_session),
) -> Whisper:
    """Record an operator whisper event."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    whisper = Whisper(call_id=call_id, **body.model_dump())
    session.add(whisper)
    await session.commit()
    await session.refresh(whisper)
    logger.info("Logged whisper for call %s.", call_id)
    return whisper


@router.post(
    "/calls/{call_id}/ended",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_verify_internal_key)],
)
async def mark_call_ended(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Mark a call as ended and trigger compliance checks."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    call.status = "ended"
    call.ended_at = datetime.now(timezone.utc)
    await session.commit()

    # Run compliance checks asynchronously but within the same request.
    try:
        await run_compliance(call_id, session)
    except Exception:
        logger.exception("Compliance checks failed for call %s", call_id)

    logger.info("Call %s marked as ended.", call_id)
    return {"ok": True}


@router.get(
    "/agents/{agent_id}",
    response_model=AgentOut,
    dependencies=[Depends(_verify_internal_key)],
)
async def get_agent_config(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Return the agent configuration for the worker to consume."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
