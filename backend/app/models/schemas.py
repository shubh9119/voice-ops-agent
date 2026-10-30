"""Pydantic models for all API request and response bodies."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


# ─── Ingest ────────────────────────────────────────────────

class DocumentInput(BaseModel):
    """A single document to ingest — either a URL or raw text."""
    url: Optional[str] = Field(None, description="URL to fetch content from")
    text: Optional[str] = Field(None, description="Raw text content")
    source: Optional[str] = Field(None, description="Source identifier (used when text is provided)")
    brand: str = Field(..., description="Brand this document is about")

    def model_post_init(self, __context):
        if not self.url and not self.text:
            raise ValueError("Each document must have either 'url' or 'text'")
        if self.url and self.text:
            raise ValueError("Provide either 'url' or 'text', not both")
        if self.text and not self.source:
            raise ValueError("'source' is required when 'text' is provided")


class IngestRequest(BaseModel):
    """Request body for POST /tenants/{tenant_id}/ingest"""
    documents: list[DocumentInput] = Field(..., min_length=1, description="List of documents to ingest")


class IngestResponse(BaseModel):
    """Response body for POST /tenants/{tenant_id}/ingest"""
    documents_stored: int
    chunks_stored: int


# ─── Ask ───────────────────────────────────────────────────

class AskRequest(BaseModel):
    """Request body for POST /tenants/{tenant_id}/ask"""
    question: str = Field(..., min_length=3, description="Question in plain English")


class Citation(BaseModel):
    """A single citation referencing a source chunk."""
    source: str
    brand: str
    chunk_text: str


class TraceEntry(BaseModel):
    """A single step in the agent's execution trace."""
    node: str
    detail: str


class AskResponse(BaseModel):
    """Response body for POST /tenants/{tenant_id}/ask"""
    answer: str
    found_in_corpus: bool
    citations: list[Citation] = []
    trace: list[TraceEntry] = []


# ─── Health ────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response body for GET /health"""
    status: str = "ok"
    version: str
    vector_db: str  # "reachable" or "unreachable"
    llm_provider: str  # "reachable" or "unreachable"


# ─── Errors ────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_type: str = "error"
