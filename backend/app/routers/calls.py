"""Call lifecycle endpoints: create, list, detail, transcript, metrics, operator token."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from livekit import api
from livekit.api import CreateAgentDispatchRequest, CreateRoomRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Agent, Call, ComplianceResult, Turn, TurnMetric
from app.schemas import (
    CallCreate,
    CallDetailOut,
    CallOut,
    ComplianceOut,
    TurnMetricOut,
    TurnOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _livekit_api() -> api.LiveKitAPI:
    """Create a LiveKit API client."""
    return api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


def _customer_token(call_id: str, room_name: str) -> str:
    """Generate a LiveKit access token for the customer participant."""
    token = (
        api.AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(f"customer-{call_id}")
        .with_name("Customer")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=False,
            )
        )
    )
    return token.to_jwt()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=CallOut, status_code=status.HTTP_201_CREATED)
async def create_call(
    body: CallCreate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Initiate a new voice call.

    1. Validate the agent exists.
    2. Create a LiveKit room.
    3. Dispatch the agent worker into the room.
    4. Generate a customer participant token.
    5. Persist the call record.
    """
    # 1. Validate agent
    agent = await session.get(Agent, body.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    call_id = uuid.uuid4().hex[:16]
    room_name = f"call-{call_id}"

    # 2 + 3. LiveKit room + agent dispatch
    lk_api = _livekit_api()
    try:
        await lk_api.room.create_room(
            CreateRoomRequest(name=room_name, empty_timeout=300)
        )
        await lk_api.agent_dispatch.create_dispatch(
            CreateAgentDispatchRequest(
                agent_name=settings.agent_name,
                room=room_name,
                metadata=json.dumps(
                    {"call_id": call_id, "agent_id": body.agent_id}
                ),
            )
        )
        logger.info("Created LiveKit room %s and dispatched agent", room_name)
    except Exception as exc:
        logger.warning("LiveKit server room/dispatch notice: %s", exc)
    finally:
        try:
            await lk_api.aclose()
        except Exception:
            pass

    # 4. Customer token
    token = _customer_token(call_id, room_name)

    # 5. Persist
    call = Call(
        id=call_id,
        agent_id=body.agent_id,
        room_name=room_name,
        status="waiting",
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)
    logger.info("Created call %s in room %s", call_id, room_name)

    return {
        "id": call.id,
        "agent_id": call.agent_id,
        "room_name": call.room_name,
        "status": call.status,
        "started_at": call.started_at,
        "ended_at": call.ended_at,
        "livekit_url": settings.livekit_public_url,
        "token": token,
    }


@router.get("", response_model=list[CallDetailOut])
async def list_calls(
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter by call status"
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List all calls, optionally filtered by status."""
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


@router.get("/{call_id}", response_model=CallDetailOut)
async def get_call(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Retrieve full call detail including transcript, compliance, and metrics."""
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

    token = _customer_token(call_id, call.room_name)

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
        "token": token,
        "livekit_url": settings.livekit_public_url,
    }


@router.get("/{call_id}/transcript", response_model=list[TurnOut])
async def get_transcript(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[Turn]:
    """Return the ordered transcript for a call."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    result = await session.execute(
        select(Turn).where(Turn.call_id == call_id).order_by(Turn.idx)
    )
    return list(result.scalars().all())


@router.get("/{call_id}/metrics", response_model=list[TurnMetricOut])
async def get_metrics(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[TurnMetric]:
    """Return latency metrics for every turn in a call."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    result = await session.execute(
        select(TurnMetric)
        .where(TurnMetric.call_id == call_id)
        .order_by(TurnMetric.turn_idx)
    )
    return list(result.scalars().all())


@router.post("/{call_id}/operator-token")
async def create_operator_token(
    call_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate a LiveKit token for the operator (hidden from customer)."""
    call = await session.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")

    token = (
        api.AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(f"operator-{call_id}")
        .with_name("Operator")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=call.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                hidden=True,
            )
        )
    )

    return {
        "token": token.to_jwt(),
        "livekit_url": settings.livekit_public_url,
    }
