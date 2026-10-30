"""Question-answering endpoint."""

import logging
import asyncio
from fastapi import APIRouter, HTTPException, Path

from app.models.schemas import (
    AskRequest,
    AskResponse,
    Citation,
    TraceEntry,
    ErrorResponse,
)
from app.agents.qa_agent import run_qa_agent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ask"])


@router.post(
    "/tenants/{tenant_id}/ask",
    response_model=AskResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid question"},
        504: {"model": ErrorResponse, "description": "LLM timeout"},
    },
)
async def ask_question(
    tenant_id: str = Path(..., min_length=1, max_length=100, description="Tenant identifier"),
    body: AskRequest = ...,
):
    """Ask a question against a tenant's ingested corpus.

    Runs the LangGraph RAG agent which:
    1. Retrieves relevant chunks from the tenant's vector namespace
    2. Grades each chunk for relevance
    3. Either generates an answer with citations, retries with a
       rewritten question, or reports that the answer is not in
       the corpus.

    Returns the answer, citations, and a full execution trace.
    """
    try:
        # Run the LangGraph agent with a timeout
        final_state = await asyncio.wait_for(
            run_qa_agent(tenant_id=tenant_id, question=body.question),
            timeout=60.0,
        )

        # Build response from final state
        citations = [
            Citation(**c) for c in final_state.get("citations", [])
        ]
        trace = [
            TraceEntry(**t) for t in final_state.get("trace", [])
        ]

        return AskResponse(
            answer=final_state.get("answer", ""),
            found_in_corpus=final_state.get("found_in_corpus", False),
            citations=citations,
            trace=trace,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="LLM request timed out. Please try again.",
        )
    except Exception as e:
        logger.exception(f"Ask failed for tenant '{tenant_id}'")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing question: {str(e)}",
        )
