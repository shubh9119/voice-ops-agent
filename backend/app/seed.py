"""Seed the database with default agent configurations."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent

logger = logging.getLogger(__name__)

# Default agents provisioned on first startup.
_DEFAULT_AGENTS = [
    {
        "name": "Acme Support",
        "system_prompt": (
            "You are a friendly and professional customer-support agent for Acme Corp. "
            "Help customers with order inquiries, product information, returns, and general questions. "
            "Be empathetic, concise, and solution-oriented. Never make promises about refunds without "
            "confirming with a supervisor first. Always follow company policy."
        ),
        "greeting": (
            "Hello! Thank you for calling Acme Corp customer support. "
            "Please note that this call is being recorded for quality and training purposes. "
            "How can I help you today?"
        ),
        "voice": "aura-2-thalia-en",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "name": "TechHelp Bot",
        "system_prompt": (
            "You are a knowledgeable technical-support agent. Help users troubleshoot software "
            "and hardware issues. Walk them through solutions step-by-step. If a problem is beyond "
            "your scope, escalate to a human specialist. Keep explanations clear and jargon-free."
        ),
        "greeting": (
            "Hi there! Welcome to TechHelp support. "
            "Just so you know, this call may be recorded for quality assurance. "
            "What technical issue can I assist you with?"
        ),
        "voice": "aura-2-thalia-en",
        "model": "llama-3.3-70b-versatile",
    },
]


async def seed_agents(session: AsyncSession) -> None:
    """Insert default agents if the table is empty."""
    result = await session.execute(select(Agent).limit(1))
    if result.scalars().first() is not None:
        logger.info("Agents table already populated – skipping seed.")
        return

    for data in _DEFAULT_AGENTS:
        session.add(Agent(**data))
    await session.commit()
    logger.info("Seeded %d default agents.", len(_DEFAULT_AGENTS))
