"""Test 1: Tenant isolation — data ingested for tenant A is not
returned when tenant B asks a question.

This test runs WITHOUT any API key (LLM is mocked).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestTenantIsolation:
    """Verify that tenant data is completely isolated."""

    def test_tenant_a_data_not_visible_to_tenant_b(self, client, mock_llm):
        """Ingest data for tenant 'acme', then query as tenant 'globex'.

        Expected: globex gets found_in_corpus=false because it has
        no data, even though acme has relevant content.
        """
        # ── Step 1: Ingest documents for tenant 'acme' ──
        ingest_payload = {
            "documents": [
                {
                    "text": (
                        "Asana is a project management tool known for its intuitive interface "
                        "and powerful task management features. Asana pricing starts at $10.99 per user "
                        "per month for the Starter plan."
                    ),
                    "source": "review-site-1",
                    "brand": "Asana",
                },
                {
                    "text": (
                        "Trello uses a kanban-style board system that is free for small teams. "
                        "Trello pricing is very competitive with a free tier and paid plans starting "
                        "at $5 per user per month."
                    ),
                    "source": "review-site-2",
                    "brand": "Trello",
                },
            ]
        }

        response = client.post("/tenants/acme/ingest", json=ingest_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["documents_stored"] == 2
        assert data["chunks_stored"] > 0

        # ── Step 2: Ask as tenant 'globex' (has no data) ──
        async def side_effect(prompt):
            prompt_str = str(prompt)
            if "relevance grader" in prompt_str.lower() or ("yes" in prompt_str.lower() and "no" in prompt_str.lower()):
                return "no"
            elif "rewrite" in prompt_str.lower() or "optimizer" in prompt_str.lower():
                return "What are the pricing details for Asana and Trello?"
            return "no"

        mock_llm.side_effect = side_effect

        ask_payload = {"question": "What do reviewers say about Asana's pricing?"}
        response = client.post("/tenants/globex/ask", json=ask_payload)
        assert response.status_code == 200
        data = response.json()

        # globex must NOT see acme's data
        assert data["found_in_corpus"] is False
        assert len(data["citations"]) == 0

    def test_tenant_a_can_access_own_data(self, client, mock_llm):
        """Ingest data for tenant 'acme' and verify acme CAN query it.

        Expected: acme gets found_in_corpus=true with citations.
        """
        # ── Step 1: Ingest for acme ──
        ingest_payload = {
            "documents": [
                {
                    "text": (
                        "Asana offers robust project management with timeline views and workload management. "
                        "The Starter plan costs $10.99 per user per month."
                    ),
                    "source": "pm-review",
                    "brand": "Asana",
                },
            ]
        }

        response = client.post("/tenants/acme/ingest", json=ingest_payload)
        assert response.status_code == 200

        # ── Step 2: Ask as acme ──
        async def side_effect(prompt):
            prompt_str = str(prompt)
            if "relevance grader" in prompt_str.lower() or ("yes" in prompt_str.lower() and "no" in prompt_str.lower()):
                return "yes"
            return (
                "Based on the reviews, Asana's Starter plan costs $10.99 per user per month "
                "and offers timeline views and workload management features."
            )

        mock_llm.side_effect = side_effect

        ask_payload = {"question": "What does Asana's pricing look like?"}
        response = client.post("/tenants/acme/ask", json=ask_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["found_in_corpus"] is True
        assert len(data["citations"]) > 0
        assert data["answer"] != ""

    def test_idempotent_ingest(self, client):
        """Ingest the same document twice — chunk count must not grow."""
        payload = {
            "documents": [
                {
                    "text": (
                        "ClickUp is an all-in-one productivity platform that replaces multiple tools. "
                        "It offers free and paid plans with rich customizability."
                    ),
                    "source": "clickup-review",
                    "brand": "ClickUp",
                },
            ]
        }

        # First ingest
        r1 = client.post("/tenants/idempotent_test/ingest", json=payload)
        assert r1.status_code == 200
        chunks_first = r1.json()["chunks_stored"]

        # Second ingest — same content
        r2 = client.post("/tenants/idempotent_test/ingest", json=payload)
        assert r2.status_code == 200
        chunks_second = r2.json()["chunks_stored"]

        assert chunks_first == chunks_second

        # Check total vectors stored in the vector store collection
        from app.services.vectorstore import VectorStoreService
        vs = VectorStoreService.get_instance()
        total_vectors = vs.collection_count("idempotent_test")

        # Total vectors should equal chunks_first, NOT chunks_first * 2
        assert total_vectors == chunks_first
