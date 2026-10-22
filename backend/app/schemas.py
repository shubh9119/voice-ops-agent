"""Pydantic schemas for request / response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AgentCreate(BaseModel):
    """Payload to create a new agent configuration."""
    name: str = Field(..., min_length=1, max_length=120)
    system_prompt: str = Field(..., min_length=1)
    greeting: str = Field(..., min_length=1)
    voice: str = Field(default="aura-2-thalia-en", max_length=60)
    model: str = Field(default="llama-3.3-70b-versatile", max_length=80)


class AgentUpdate(BaseModel):
    """Partial update for an agent – all fields optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    system_prompt: Optional[str] = Field(default=None, min_length=1)
    greeting: Optional[str] = Field(default=None, min_length=1)
    voice: Optional[str] = Field(default=None, max_length=60)
    model: Optional[str] = Field(default=None, max_length=80)


class AgentOut(BaseModel):
    """Agent data returned to callers."""
    id: str
    name: str
    system_prompt: str
    greeting: str
    voice: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Turn
# ---------------------------------------------------------------------------

class TurnCreate(BaseModel):
    """A transcript turn submitted by the agent worker."""
    idx: int
    speaker: str = Field(..., pattern=r"^(agent|user)$")
    text: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    interrupted: bool = False


class TurnOut(BaseModel):
    """A transcript turn returned to callers."""
    idx: int
    speaker: str
    text: str
    started_at: datetime
    interrupted: bool = False

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------

class WhisperCreate(BaseModel):
    """Payload to record an operator whisper."""
    text: str = Field(..., min_length=1)
    sent_at: datetime
    applied_at_turn: Optional[int] = None


class WhisperOut(BaseModel):
    """Whisper data returned to callers."""
    id: int
    call_id: str
    text: str
    sent_at: datetime
    applied_at_turn: Optional[int] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# TurnMetric
# ---------------------------------------------------------------------------

class TurnMetricCreate(BaseModel):
    """Latency metrics for one turn, submitted by the agent worker."""
    turn_idx: int
    vad_end_ms: Optional[float] = None
    stt_final_ms: Optional[float] = None
    llm_ttft_ms: Optional[float] = None
    tts_ttfb_ms: Optional[float] = None
    audio_published_ms: Optional[float] = None
    e2e_ms: Optional[float] = None


class TurnMetricOut(BaseModel):
    """Latency metrics returned to callers."""
    turn_idx: int
    vad_end_ms: Optional[float] = None
    stt_final_ms: Optional[float] = None
    llm_ttft_ms: Optional[float] = None
    tts_ttfb_ms: Optional[float] = None
    audio_published_ms: Optional[float] = None
    e2e_ms: Optional[float] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

class ComplianceOut(BaseModel):
    """A single compliance check result."""
    rule: str
    method: str
    status: str
    offending_line: Optional[str] = None
    offending_turn_idx: Optional[int] = None
    detail: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Call
# ---------------------------------------------------------------------------

class CallCreate(BaseModel):
    """Payload to initiate a new call."""
    agent_id: str


class CallOut(BaseModel):
    """Minimal call info returned after creation."""
    id: str
    agent_id: str
    room_name: str
    status: str
    livekit_url: str
    token: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CallDetailOut(BaseModel):
    """Full call data including transcript, compliance results, and metrics."""
    id: str
    agent_id: str
    room_name: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    transcript: list[TurnOut] = []
    compliance: list[ComplianceOut] = []
    metrics: list[TurnMetricOut] = []
    token: Optional[str] = None
    livekit_url: Optional[str] = None

    model_config = {"from_attributes": True}
