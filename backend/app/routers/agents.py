"""Agent CRUD endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Agent
from app.schemas import AgentCreate, AgentOut, AgentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Create a new agent configuration."""
    agent = Agent(**body.model_dump())
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    logger.info("Created agent %s (%s)", agent.id, agent.name)
    return agent


@router.get("", response_model=list[AgentOut])
async def list_agents(
    session: AsyncSession = Depends(get_session),
) -> list[Agent]:
    """List all agent configurations."""
    result = await session.execute(select(Agent).order_by(Agent.created_at))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Retrieve a single agent by ID."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Partially update an agent configuration."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )

    for field, value in updates.items():
        setattr(agent, field, value)

    await session.commit()
    await session.refresh(agent)
    logger.info("Updated agent %s: %s", agent.id, list(updates.keys()))
    return agent
