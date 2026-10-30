"""LangGraph agent state definition."""

from typing import TypedDict, Annotated
from app.models.schemas import Citation, TraceEntry


class AgentState(TypedDict):
    """State object passed through the LangGraph RAG agent.

    Holds everything the graph needs from start to finish:
    the tenant context, the question, retrieved/graded chunks,
    retry tracking, and the final answer with citations.
    """
    tenant_id: str
    question: str
    original_question: str
    retrieved_chunks: list[dict]
    relevant_chunks: list[dict]
    retry_count: int
    answer: str
    found_in_corpus: bool
    citations: list[dict]
    trace: list[dict]
