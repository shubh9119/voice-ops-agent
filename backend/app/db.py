"""Async SQLAlchemy engine, session factory, and FastAPI dependency."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level state – initialised at startup via ``init_engine()``.
_engine = None
_async_session: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    """Create the async engine and session maker from current settings."""
    global _engine, _async_session
    logger.info("Initialising database engine: %s", settings.database_url)
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    _async_session = async_sessionmaker(_engine, expire_on_commit=False)


async def create_all() -> None:
    """Create all ORM tables (idempotent)."""
    from app.models import Base  # noqa: local import to avoid circular deps

    if _engine is None:
        raise RuntimeError("Engine not initialised – call init_engine() first")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session and closes it after use."""
    if _async_session is None:
        raise RuntimeError("Engine not initialised – call init_engine() first")
    async with _async_session() as session:
        yield session
