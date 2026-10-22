"""Operator-facing endpoints.

These routes are authenticated with the ``X-Operator-Key`` header matching
``settings.operator_api_key``.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Call, ComplianceResult, Turn, TurnMetric, Whisper
from app.schemas import (
    CallDetailOut,
    ComplianceOut,
    TurnMetricOut,
    TurnOut,
    WhisperOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operator", tags=["operator"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def _verify_operator_key(
    x_operator_key: str = Header(..., alias="X-Operator-Key"),
) -> None:
    """Reject requests without a valid operator API key."""
    if x_operator_key != settings.operator_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid operator API key",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/calls",
    response_model=list[CallDetailOut],
    dependencies=[Depends(_verify_operator_key)],
)
async def operator_list_calls(
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter by call status"
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List all calls for the operator dashboard."""
    stmt = select(Call).order_by(Call.started_at.desc().nullslast())
    if status_filter:
        stmt = stmt.where(Call.status == status_filter)
    result = await session.execute(stmt)
    calls = result.scalars().all()

    out: list[dict] = []
    for call in calls:
        turns = (
            await session.execute(
                select(Turn).where(Turn.call_id == call.id).order_by(Turn.idx)
            )
        ).scalars().all()
        compliance = (
            await session.execute(
                select(ComplianceResult).where(
                    ComplianceResult.call_id == call.id
                )
            )
        ).scalars().all()
        metrics = (
            await session.execute(
                select(TurnMetric)
                .where(TurnMetric.call_id == call.id)
                .order_by(TurnMetric.turn_idx)
            )
        ).scalars().all()
        out.append(
            {
                "id": call.id,
                "agent_id": call.agent_id,
                "room_name": call.room_name,
                "status": call.status,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "transcript": turns,
                "compliance": compliance,
                "metrics": metrics,
            }
        )
    return out


@router.get(
    "/calls/{call_id}",
    response_model=CallDetailOut,
    dependencies=[Depends(_verify_operator_key)],
)
async def operator_get_call(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get full call detail for the operator."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    turns = (
        await session.execute(
            select(Turn).where(Turn.call_id == call_id).order_by(Turn.idx)
        )
    ).scalars().all()
    compliance = (
        await session.execute(
            select(ComplianceResult).where(
                ComplianceResult.call_id == call_id
            )
        )
    ).scalars().all()
    metrics = (
        await session.execute(
            select(TurnMetric)
            .where(TurnMetric.call_id == call_id)
            .order_by(TurnMetric.turn_idx)
        )
    ).scalars().all()

    return {
        "id": call.id,
        "agent_id": call.agent_id,
        "room_name": call.room_name,
        "status": call.status,
        "started_at": call.started_at,
        "ended_at": call.ended_at,
        "transcript": turns,
        "compliance": compliance,
        "metrics": metrics,
    }


@router.get(
    "/calls/{call_id}/whispers",
    response_model=list[WhisperOut],
    dependencies=[Depends(_verify_operator_key)],
)
async def operator_get_whispers(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[Whisper]:
    """Return all whispers for a call."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    result = await session.execute(
        select(Whisper)
        .where(Whisper.call_id == call_id)
        .order_by(Whisper.sent_at)
    )
    return list(result.scalars().all())
