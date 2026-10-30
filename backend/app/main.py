"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import health, ingest, ask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"LLM model: {settings.LLM_MODEL}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    logger.info(f"ChromaDB dir: {settings.CHROMA_PERSIST_DIR}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Omnibound Brand Q&A Agent",
    description=(
        "RAG-powered brand research API. Ingest web pages and articles "
        "about brands, then ask questions answered from that corpus."
    ),
    version=get_settings().APP_VERSION,
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(ask.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unhandled errors."""
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_type": "internal"},
    )
