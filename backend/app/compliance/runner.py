"""Compliance orchestration runner executed upon call completion."""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.deterministic import (
    check_no_operator_mention,
    check_recording_disclosure,
)
from app.compliance.llm_check import check_no_refund_promise
from app.config import get_settings
from app.models import Call, ComplianceResult, Turn

logger = logging.getLogger(__name__)


async def run_compliance(call_id: str, session: AsyncSession) -> list[ComplianceResult]:
    """Execute all compliance audits for a completed call and persist the results."""
    logger.info("Executing compliance evaluation for call: %s", call_id)

    # 1. Fetch Call
    call = await session.get(Call, call_id)
    if not call:
        logger.error("Call %s not found for compliance check", call_id)
        return []

    # 2. Fetch turns ordered by idx
    stmt = select(Turn).where(Turn.call_id == call_id).order_by(Turn.idx.asc())
    result = await session.execute(stmt)
    turn_rows = result.scalars().all()

    turn_dicts: list[dict[str, Any]] = [
        {
            "idx": t.idx,
            "speaker": t.speaker,
            "text": t.text,
            "started_at": t.started_at,
            "ended_at": t.ended_at,
            "interrupted": t.interrupted,
        }
        for t in turn_rows
    ]

    settings = get_settings()

    # Rule 1: Recording Disclosure (Deterministic, 30s)
    res_recording = check_recording_disclosure(turn_dicts, call.started_at)

    # Rule 2: Operator secrecy (Deterministic)
    res_operator = check_no_operator_mention(turn_dicts)

    # Rule 3: No refund promise (LLM)
    # Check OpenAI key or Groq key
    openai_key = (settings.openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if openai_key.startswith("your-"):
        openai_key = ""

    groq_key = (settings.groq_api_key or settings.llm_api_key or os.getenv("GROQ_API_KEY") or "").strip()
    if groq_key.startswith("your-"):
        groq_key = ""

    if openai_key:
        api_key = openai_key
        base_url = None
        model = settings.llm_compliance_model
    elif groq_key:
        api_key = groq_key
        base_url = "https://api.groq.com/openai/v1"
        model = "llama-3.3-70b-versatile"
    else:
        api_key = ""
        base_url = None
        model = settings.llm_compliance_model

    res_refund = await check_no_refund_promise(
        turns=turn_dicts,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    all_results = [res_recording, res_operator, res_refund]

    # Delete existing compliance results if re-running
    await session.execute(
        delete(ComplianceResult).where(ComplianceResult.call_id == call_id)
    )

    db_entries: list[ComplianceResult] = []
    for r in all_results:
        entry = ComplianceResult(
            call_id=call_id,
            rule=r["rule"],
            method=r["method"],
            status=r["status"],
            offending_line=r.get("offending_line"),
            offending_turn_idx=r.get("offending_turn_idx"),
            detail=r.get("detail", ""),
        )
        session.add(entry)
        db_entries.append(entry)

    await session.commit()
    logger.info("Compliance results saved for call %s: %s", call_id, [e.status for e in db_entries])
    return db_entries
