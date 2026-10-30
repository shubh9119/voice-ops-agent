"""LangGraph RAG agent for brand Q&A.

Implements a StateGraph with three nodes and one conditional edge:

    START → retrieve → grade → decision
                                 ├─ relevant chunks → answer → END
                                 ├─ nothing & retry_count==0 → rewrite → retrieve
                                 └─ nothing & retried → END (not found)

Every node appends to `trace` for full observability.
"""

import asyncio
from typing import Literal

from app.models.state import AgentState
from app.services.vectorstore import VectorStoreService
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.config import get_settings

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    END = "__end__"


# ──────────────────────────────────────────────────────────
# Node functions
# ──────────────────────────────────────────────────────────

async def retrieve_node(state: AgentState) -> dict:
    """Retrieve top-K chunks from the vector store for this tenant."""
    settings = get_settings()
    embedding_service = EmbeddingService.get_instance()
    vectorstore = VectorStoreService.get_instance()

    question = state["question"]
    tenant_id = state["tenant_id"]

    query_embedding = await embedding_service.embed_query(question)

    chunks = vectorstore.query(
        tenant_id=tenant_id,
        query_embedding=query_embedding,
        n_results=settings.TOP_K_RESULTS,
    )

    trace_entry = {
        "node": "retrieve",
        "detail": f"{len(chunks)} chunks retrieved for tenant '{tenant_id}'",
    }

    return {
        "retrieved_chunks": chunks,
        "trace": state.get("trace", []) + [trace_entry],
    }


async def grade_node(state: AgentState) -> dict:
    """Grade each retrieved chunk for relevance to the question.

    Asks the LLM: 'Does this chunk help answer the question? Reply yes or no.'
    Only chunks graded 'yes' are kept in relevant_chunks.
    """
    llm = LLMService.get_instance()
    question = state["question"]
    retrieved = state.get("retrieved_chunks", [])
    relevant = []
    rejected_count = 0

    for chunk in retrieved:
        doc_text = chunk.get("document", "")
        prompt = (
            f"You are a relevance grader. Given a question and a text chunk, "
            f"decide if the chunk contains information that helps answer the question.\n\n"
            f"Question: {question}\n\n"
            f"Chunk: {doc_text}\n\n"
            f"Reply with ONLY 'yes' or 'no'. Nothing else."
        )

        try:
            response = await llm.ainvoke(prompt)
            grade = str(response).strip().lower()

            if "yes" in grade:
                relevant.append(chunk)
            else:
                rejected_count += 1
        except Exception:
            relevant.append(chunk)

    trace_entry = {
        "node": "grade",
        "detail": f"{len(relevant)} relevant, {rejected_count} rejected",
    }

    return {
        "relevant_chunks": relevant,
        "trace": state.get("trace", []) + [trace_entry],
    }


def decide_next(state: AgentState) -> Literal["answer", "rewrite", "not_found"]:
    """Conditional edge: decide next step based on grading results.

    - If relevant chunks exist → go to answer
    - If no relevant chunks and retry_count == 0 → rewrite and retry
    - If no relevant chunks and already retried → end with not_found
    """
    relevant = state.get("relevant_chunks", [])
    retry_count = state.get("retry_count", 0)
    max_retries = get_settings().MAX_RETRIES

    if len(relevant) > 0:
        return "answer"
    elif retry_count < max_retries:
        return "rewrite"
    else:
        return "not_found"


async def rewrite_node(state: AgentState) -> dict:
    """Rewrite question to improve retrieval on retry."""
    llm = LLMService.get_instance()
    question = state["question"]

    prompt = (
        f"You are a search query optimizer. The following question did not return "
        f"relevant results from a document search. Rewrite it to be more specific "
        f"and use different keywords that might match stored content better.\n\n"
        f"Original question: {question}\n\n"
        f"Rewritten question (just the question, nothing else):"
    )

    try:
        rewritten = await llm.ainvoke(prompt)
        rewritten = str(rewritten).strip().strip('"').strip("'")
    except Exception:
        rewritten = question

    trace_entry = {
        "node": "rewrite",
        "detail": f"Question rewritten: '{rewritten[:100]}...'",
    }

    return {
        "question": rewritten,
        "retry_count": state.get("retry_count", 0) + 1,
        "retrieved_chunks": [],
        "relevant_chunks": [],
        "trace": state.get("trace", []) + [trace_entry],
    }


async def answer_node(state: AgentState) -> dict:
    """Generate final answer using ONLY relevant chunks."""
    llm = LLMService.get_instance()
    relevant = state.get("relevant_chunks", [])
    question = state.get("original_question", state["question"])

    context_parts = []
    for i, chunk in enumerate(relevant, 1):
        source = chunk.get("metadata", {}).get("source", "unknown")
        brand = chunk.get("metadata", {}).get("brand", "unknown")
        context_parts.append(
            f"[Source {i}: {source} | Brand: {brand}]\n{chunk.get('document', '')}"
        )

    context = "\n\n".join(context_parts)

    prompt = (
        f"You are a helpful brand research assistant. Answer the following question "
        f"using ONLY the provided context. Do not add information from your own knowledge.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Provide a clear, concise answer (2-4 sentences) with specific details from the sources."
    )

    try:
        answer_text = str(await llm.ainvoke(prompt))
    except Exception as e:
        answer_text = f"Error generating answer: {str(e)}"

    citations = []
    for chunk in relevant:
        meta = chunk.get("metadata", {})
        citations.append({
            "source": meta.get("source", "unknown"),
            "brand": meta.get("brand", "unknown"),
            "chunk_text": chunk.get("document", "")[:300],
        })

    trace_entry = {
        "node": "answer",
        "detail": f"Answer generated from {len(relevant)} chunks",
    }

    return {
        "answer": answer_text,
        "found_in_corpus": True,
        "citations": citations,
        "trace": state.get("trace", []) + [trace_entry],
    }


async def not_found_node(state: AgentState) -> dict:
    """Terminal node when no relevant content is found."""
    trace_entry = {
        "node": "not_found",
        "detail": "No relevant content found after retry; answer not in corpus",
    }

    return {
        "answer": (
            "The answer to your question was not found in the ingested corpus. "
            "The documents stored for your tenant do not contain information "
            "relevant to this query."
        ),
        "found_in_corpus": False,
        "citations": [],
        "trace": state.get("trace", []) + [trace_entry],
    }


# ──────────────────────────────────────────────────────────
# Graph implementation
# ──────────────────────────────────────────────────────────

class FallbackExecutionGraph:
    """Fallback runner executing the identical LangGraph state graph flow."""

    async def ainvoke(self, state: AgentState) -> AgentState:
        curr = dict(state)
        while True:
            # Step 1: retrieve
            res = await retrieve_node(curr)
            curr.update(res)

            # Step 2: grade
            res = await grade_node(curr)
            curr.update(res)

            # Step 3: decision
            decision = decide_next(curr)
            if decision == "answer":
                res = await answer_node(curr)
                curr.update(res)
                return curr
            elif decision == "rewrite":
                res = await rewrite_node(curr)
                curr.update(res)
                # Loop back to retrieve
                continue
            else:  # not_found
                res = await not_found_node(curr)
                curr.update(res)
                return curr


def build_qa_graph():
    """Build LangGraph StateGraph (or fallback graph when LangGraph is absent)."""
    if HAS_LANGGRAPH:
        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("grade", grade_node)
        graph.add_node("rewrite", rewrite_node)
        graph.add_node("answer", answer_node)
        graph.add_node("not_found", not_found_node)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges(
            "grade",
            decide_next,
            {
                "answer": "answer",
                "rewrite": "rewrite",
                "not_found": "not_found",
            },
        )
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("answer", END)
        graph.add_edge("not_found", END)
        return graph.compile()
    else:
        return FallbackExecutionGraph()


_compiled_graph = None


def get_qa_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_qa_graph()
    return _compiled_graph


def reset_qa_graph():
    global _compiled_graph
    _compiled_graph = None


async def run_qa_agent(tenant_id: str, question: str) -> AgentState:
    graph = get_qa_graph()

    initial_state: AgentState = {
        "tenant_id": tenant_id,
        "question": question,
        "original_question": question,
        "retrieved_chunks": [],
        "relevant_chunks": [],
        "retry_count": 0,
        "answer": "",
        "found_in_corpus": False,
        "citations": [],
        "trace": [],
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state
