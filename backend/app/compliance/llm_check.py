"""LLM-based compliance checking with structured output and verification."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict compliance auditor for customer support calls.
Your task is to analyze the conversation transcript and determine if the AGENT promised a refund to the customer.

RULES:
- A "refund promise" occurs when the agent commits to giving money back, issuing a credit/refund, or assuring the customer they will be refunded (e.g., "I'll issue a full refund", "We will refund your payment", "You will get your money back").
- Simply stating refund policies (e.g., "Our policy requires a receipt for refunds", "Refunds are processed by billing") is NOT a promise.
- Asking about refunds or denying refunds (e.g., "I cannot promise a refund") is NOT a violation.
- Customer requesting a refund is NOT an agent violation. ONLY check the AGENT's speech.

You MUST respond with valid JSON adhering to this exact schema:
{
  "passed": true | false,
  "offending_line_index": integer | null,
  "offending_line": string | null,
  "reason": string
}
"""


class RefundCheckSchema(BaseModel):
    passed: bool
    offending_line_index: int | None = None
    offending_line: str | None = None
    reason: str = Field(default="")


async def check_no_refund_promise(
    turns: list[dict[str, Any]],
    api_key: str,
    base_url: str | None = None,
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """Check if the agent promised a refund in the call transcript using an LLM.

    Validates that any reported offending_line actually appears in an agent turn.
    """
    if not api_key:
        logger.warning("No LLM API key configured for compliance check; marking inconclusive.")
        return {
            "rule": "no_refund_promise",
            "method": "llm",
            "status": "inconclusive",
            "offending_line": None,
            "offending_turn_idx": None,
            "detail": "LLM API key not configured. Set OPENAI_API_KEY or GROQ_API_KEY.",
        }

    # Format transcript with index and speaker labels
    agent_turns_text = []
    lines = []
    for t in turns:
        idx = t.get("idx", 0)
        speaker = str(t.get("speaker", "")).upper()
        text = t.get("text", "")
        lines.append(f"[{idx}] {speaker}: {text}")
        if speaker == "AGENT":
            agent_turns_text.append((idx, text))

    if not agent_turns_text:
        return {
            "rule": "no_refund_promise",
            "method": "llm",
            "status": "pass",
            "offending_line": None,
            "offending_turn_idx": None,
            "detail": "No agent utterances found in transcript.",
        }

    transcript_str = "\n".join(lines)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    last_error = ""
    for attempt in range(2):  # Retry once on failure
        try:
            response = await client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Please audit the following transcript for unauthorized refund promises:\n\n{transcript_str}",
                    },
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            schema = RefundCheckSchema.model_validate(parsed)

            if schema.passed:
                return {
                    "rule": "no_refund_promise",
                    "method": "llm",
                    "status": "pass",
                    "offending_line": None,
                    "offending_turn_idx": None,
                    "detail": schema.reason or "No refund was promised by the agent.",
                }

            # Failure: Validate that the reported offending line exists in the transcript
            offending = schema.offending_line or ""
            verified = False
            matched_idx = schema.offending_line_index

            for a_idx, a_text in agent_turns_text:
                if offending and (offending.lower() in a_text.lower() or a_text.lower() in offending.lower()):
                    verified = True
                    matched_idx = a_idx
                    break
                if matched_idx is not None and matched_idx == a_idx:
                    verified = True
                    break

            if not verified:
                if attempt == 0:
                    logger.warning("Offending line '%s' not verified in transcript; retrying...", offending)
                    continue
                return {
                    "rule": "no_refund_promise",
                    "method": "llm",
                    "status": "inconclusive",
                    "offending_line": schema.offending_line,
                    "offending_turn_idx": schema.offending_line_index,
                    "detail": f"LLM reported a violation ('{schema.offending_line}') but text could not be verified in agent turns.",
                }

            return {
                "rule": "no_refund_promise",
                "method": "llm",
                "status": "fail",
                "offending_line": schema.offending_line,
                "offending_turn_idx": matched_idx,
                "detail": schema.reason or "Agent explicitly promised a refund to the customer.",
            }

        except Exception as e:
            last_error = str(e)
            logger.warning("LLM compliance check attempt %d failed: %s", attempt + 1, e)

    return {
        "rule": "no_refund_promise",
        "method": "llm",
        "status": "inconclusive",
        "offending_line": None,
        "offending_turn_idx": None,
        "detail": f"LLM check failed after retry: {last_error}",
    }
