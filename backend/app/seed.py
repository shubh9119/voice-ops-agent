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
            "You are a friendly, helpful, and professional customer-support voice agent for Acme Corp. "
            "Company context and product catalog:\n"
            "- Acme Smart Widget: $99, our flagship IoT smart home controller with 1-year warranty.\n"
            "- Acme Cloud Pro: $29/month subscription offering automated cloud backups and security alerts.\n"
            "- Acme Home Hub: $149, central smart home bridge connecting zigbee and wifi devices.\n"
            "- Shipping: Free standard shipping (3-5 business days) on orders over $50. Express shipping is $15 (1-2 business days).\n"
            "- Return Policy: 30-day money-back guarantee for items in original packaging. "
            "IMPORTANT: As a support agent, you can explain the return policy, but you MUST NEVER unilaterally promise or guarantee an immediate cash refund on this call without supervisor sign-off.\n"
            "Style: Speak in a natural, polite, and concise tone (1 to 2 sentences per response max, perfect for phone voice). Answer customer questions about products, orders, and policies directly and accurately."
        ),
        "greeting": (
            "Hello! Thank you for calling Acme Corp customer support. "
            "Please note that this call is being recorded for quality and training purposes. "
            "How can I help you today?"
        ),
        "voice": "aura-2-thalia-en",
        "model": "qwen/qwen3.8-27b",
    },
    {
        "name": "TechHelp Bot",
        "system_prompt": (
            "You are a knowledgeable technical-support agent for TechHelp. "
            "Help users troubleshoot software and hardware issues step-by-step. "
            "Keep explanations clear, concise (1-2 sentences per turn), and jargon-free. "
            "If a problem is beyond your scope, offer to escalate to a specialist."
        ),
        "greeting": (
            "Hi there! Welcome to TechHelp support. "
            "Just so you know, this call may be recorded for quality assurance. "
            "What technical issue can I assist you with today?"
        ),
        "voice": "aura-2-thalia-en",
        "model": "qwen/qwen3.8-27b",
    },
]


async def seed_agents(session: AsyncSession) -> None:
    """Populate default agents if the agents table is empty."""
    result = await session.execute(select(Agent))
    existing = result.scalars().first()

    if existing is not None:
        logger.debug("Agents already exist in the database; skipping seed.")
        return

    logger.info("Seeding default agent configurations...")
    for data in _DEFAULT_AGENTS:
        agent = Agent(**data)
        session.add(agent)

    await session.commit()
    logger.info("Seeded %d default agents.", len(_DEFAULT_AGENTS))
