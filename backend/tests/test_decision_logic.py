"""Test 2: Decision logic — the LangGraph agent takes the correct
path based on chunk relevance.

Three scenarios tested:
1. Relevant chunks found → answer generated
2. No relevant chunks on first try → rewrite + retry → not found
3. Empty tenant → not found

All tests run WITHOUT an API key (LLM is mocked).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestDecisionLogic:
    """Verify the LangGraph conditional edge logic."""

    def test_relevant_chunks_produce_answer(self, client, mock_llm):
        """When chunks are relevant, the agent generates an answer.

        Flow: retrieve → grade (yes) → answer → END
        """
        client.post("/tenants/decision_test/ingest", json={
            "documents": [{
                "text": (
                    "Monday.com is a work operating system that helps teams plan and track projects. "
                    "Pricing starts at $9 per seat per month with a minimum of 3 seats."
                ),
                "source": "monday-review",
                "brand": "Monday.com",
            }]
        })

        async def side_effect(prompt):
            prompt_str = str(prompt)
            if "relevance grader" in prompt_str.lower() or ("yes" in prompt_str.lower() and "no" in prompt_str.lower()):
                return "yes"
            return "Monday.com pricing starts at $9 per seat per month."

        mock_llm.side_effect = side_effect

        response = client.post("/tenants/decision_test/ask", json={
            "question": "How much does Monday.com cost?"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["found_in_corpus"] is True
        assert len(data["citations"]) > 0

        # Check trace shows the correct path
        trace_nodes = [t["node"] for t in data["trace"]]
        assert "retrieve" in trace_nodes
        assert "grade" in trace_nodes
        assert "answer" in trace_nodes
        assert "not_found" not in trace_nodes

    def test_no_relevant_chunks_triggers_retry(self, client, mock_llm):
        """When no chunks are relevant, the agent rewrites and retries.

        Flow: retrieve → grade (no) → rewrite → retrieve → grade (no) → not_found
        """
        client.post("/tenants/retry_test/ingest", json={
            "documents": [{
                "text": "Monday.com helps teams collaborate on projects with boards and automations.",
                "source": "monday-article",
                "brand": "Monday.com",
            }]
        })

        async def side_effect(prompt):
            prompt_str = str(prompt)
            if "relevance grader" in prompt_str.lower() or ("yes" in prompt_str.lower() and "no" in prompt_str.lower()):
                return "no"
            elif "rewrite" in prompt_str.lower() or "optimizer" in prompt_str.lower():
                return "What is the capital city of France in Europe?"
            return "no"

        mock_llm.side_effect = side_effect

        response = client.post("/tenants/retry_test/ask", json={
            "question": "What is the capital of France?"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["found_in_corpus"] is False
        assert len(data["citations"]) == 0

        # Check trace shows the retry path
        trace_nodes = [t["node"] for t in data["trace"]]
        assert "retrieve" in trace_nodes
        assert "grade" in trace_nodes
        assert "rewrite" in trace_nodes
        assert "not_found" in trace_nodes

    def test_empty_tenant_returns_not_found(self, client, mock_llm):
        """A tenant with no data should return not_found.

        Flow: retrieve (0 chunks) → grade (0 relevant) → rewrite →
              retrieve (0 chunks) → grade (0 relevant) → not_found
        """
        async def side_effect(prompt):
            return "no"

        mock_llm.side_effect = side_effect

        response = client.post("/tenants/empty_tenant/ask", json={
            "question": "Tell me about project management tools."
        })

        assert response.status_code == 200
        data = response.json()
        assert data["found_in_corpus"] is False
        assert len(data["citations"]) == 0
        assert (
            "not found" in data["answer"].lower()
            or "not in" in data["answer"].lower()
            or "not contain" in data["answer"].lower()
        )
