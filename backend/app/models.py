"""SQLAlchemy ORM models for the voice AI agent system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase


def _utcnow() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _shortuuid() -> str:
    """Return a 16-char hex ID from uuid4."""
    return uuid.uuid4().hex[:16]


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


class Agent(Base):
    """An AI agent configuration (persona, prompt, voice)."""

    __tablename__ = "agents"

    id: str = Column(String(16), primary_key=True, default=_shortuuid)
    name: str = Column(String(120), nullable=False)
    system_prompt: str = Column(Text, nullable=False)
    greeting: str = Column(Text, nullable=False)  # must mention "recorded"
    voice: str = Column(String(60), default="aura-2-thalia-en")
    model: str = Column(String(80), default="llama-3.3-70b-versatile")
    created_at: datetime = Column(DateTime, default=_utcnow)


class Call(Base):
    """A single voice call session."""

    __tablename__ = "calls"

    id: str = Column(String(16), primary_key=True, default=_shortuuid)
    agent_id: str = Column(String(16), ForeignKey("agents.id"), nullable=False)
    room_name: str = Column(String(80), nullable=False)
    status: str = Column(String(20), default="waiting")  # waiting | active | ended
    started_at: datetime | None = Column(DateTime, nullable=True)
    ended_at: datetime | None = Column(DateTime, nullable=True)


class Turn(Base):
    """A single utterance in a call transcript."""

    __tablename__ = "turns"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    call_id: str = Column(String(16), ForeignKey("calls.id"), nullable=False, index=True)
    idx: int = Column(Integer, nullable=False)
    speaker: str = Column(String(10), nullable=False)  # "agent" | "user"
    text: str = Column(Text, nullable=False)
    started_at: datetime = Column(DateTime, nullable=False)
    ended_at: datetime | None = Column(DateTime, nullable=True)
    interrupted: bool = Column(Boolean, default=False)


class Whisper(Base):
    """An operator whisper sent during a live call."""

    __tablename__ = "whispers"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    call_id: str = Column(String(16), ForeignKey("calls.id"), nullable=False, index=True)
    text: str = Column(Text, nullable=False)
    sent_at: datetime = Column(DateTime, nullable=False)
    applied_at_turn: int | None = Column(Integer, nullable=True)


class TurnMetric(Base):
    """Latency metrics for a single agent response turn."""

    __tablename__ = "turn_metrics"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    call_id: str = Column(String(16), ForeignKey("calls.id"), nullable=False, index=True)
    turn_idx: int = Column(Integer, nullable=False)
    vad_end_ms: float | None = Column(Float, nullable=True)
    stt_final_ms: float | None = Column(Float, nullable=True)
    llm_ttft_ms: float | None = Column(Float, nullable=True)
    tts_ttfb_ms: float | None = Column(Float, nullable=True)
    audio_published_ms: float | None = Column(Float, nullable=True)
    e2e_ms: float | None = Column(Float, nullable=True)


class ComplianceResult(Base):
    """Result of a compliance check on a completed call."""

    __tablename__ = "compliance_results"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    call_id: str = Column(String(16), ForeignKey("calls.id"), nullable=False, index=True)
    rule: str = Column(String(60), nullable=False)
    method: str = Column(String(20), nullable=False)  # "deterministic" | "llm"
    status: str = Column(String(20), nullable=False)  # "pass" | "fail" | "inconclusive"
    offending_line: str | None = Column(Text, nullable=True)
    offending_turn_idx: int | None = Column(Integer, nullable=True)
    detail: str = Column(Text, default="")
