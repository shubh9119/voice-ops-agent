"""API endpoint tests for FastAPI backend."""

import os
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone

# Ensure in-memory or temp sqlite for testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ["OPERATOR_API_KEY"] = "test-operator-key"

from app.db import init_engine, create_all, get_session
from app.models import Call
from app.main import create_app
from app.seed import seed_agents


@pytest_asyncio.fixture
async def test_client():
    init_engine()
    await create_all()

    async for session in get_session():
        await seed_agents(session)
        break

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(test_client):
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_list_agents(test_client):
    response = await test_client.get("/agents")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) >= 2  # Seeded agents


@pytest.mark.asyncio
async def test_create_agent(test_client):
    payload = {
        "name": "Custom Test Agent",
        "system_prompt": "You are a test agent.",
        "greeting": "Hello, this call is recorded. How can I help?",
        "voice": "aura-2-thalia-en",
        "model": "llama-3.3-70b-versatile",
    }
    response = await test_client.post("/agents", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Custom Test Agent"
    assert created["id"] is not None


@pytest.mark.asyncio
async def test_internal_call_lifecycle(test_client):
    # 1. First get an agent ID
    agents_res = await test_client.get("/agents")
    agent_id = agents_res.json()[0]["id"]

    # 2. Add turns directly via internal API
    call_id = "test-call-12345"
    headers = {"X-Internal-Key": "test-internal-key"}

    # Seed call in database
    async for s in get_session():
        s.add(Call(id=call_id, agent_id=agent_id, room_name=f"call-{call_id}", status="waiting"))
        await s.commit()
        break

    # Register start
    start_res = await test_client.post(f"/internal/calls/{call_id}/started", headers=headers)
    assert start_res.status_code == 200

    # Add a turn with recording disclosure
    now = datetime.now(timezone.utc).isoformat()
    turns_payload = [
        {
            "idx": 0,
            "speaker": "agent",
            "text": "Hello, this call is recorded for quality assurance.",
            "started_at": now,
            "interrupted": False,
        },
        {
            "idx": 1,
            "speaker": "user",
            "text": "Hello, I want to ask about my bill.",
            "started_at": now,
            "interrupted": False,
        },
    ]
    turns_res = await test_client.post(
        f"/internal/calls/{call_id}/turns",
        json=turns_payload,
        headers=headers,
    )
    assert turns_res.status_code == 200

    # End call and trigger compliance
    end_res = await test_client.post(f"/internal/calls/{call_id}/ended", headers=headers)
    assert end_res.status_code == 200

    # Verify call detail and compliance
    call_res = await test_client.get(f"/calls/{call_id}")
    assert call_res.status_code == 200
    data = call_res.json()
    assert data["status"] == "ended"
    assert len(data["transcript"]) == 2
    assert len(data["compliance"]) >= 1

    # Check that recording disclosure passed
    rec_rule = next((c for c in data["compliance"] if c["rule"] == "recording_disclosure_30s"), None)
    assert rec_rule is not None
    assert rec_rule["status"] == "pass"
