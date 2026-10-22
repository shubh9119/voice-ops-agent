"""FastAPI application factory and lifespan handler."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import create_all, get_session, init_engine
from app.seed import seed_agents
from app.routers import agents, calls, internal, operator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle for the application."""
    logger.info("Starting up …")
    init_engine()
    await create_all()

    # Seed default agents inside a fresh session.
    async for session in get_session():
        await seed_agents(session)
        break  # only one iteration needed

    yield  # ← application runs here

    logger.info("Shutting down …")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title="VoiceOps AI – Backend",
        description="Operator-guided voice AI agent system",
        version="0.1.0",
        lifespan=_lifespan,
    )

    # CORS – wide open for local dev; lock down in production.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    application.include_router(agents.router)
    application.include_router(calls.router)
    application.include_router(internal.router)
    application.include_router(operator.router)

    @application.get("/health", tags=["health"])
    async def health() -> dict:
        """Liveness probe."""
        return {"ok": True}

    return application


# Module-level app instance used by ``uvicorn app.main:app``.
app = create_app()
