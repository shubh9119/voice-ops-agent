"""Script to seed a realistic completed call with turns, compliance, and metrics.

Usage:
    python scripts/seed_demo_call.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db import init_engine, create_all, get_session
from app.models import Agent, Call, Turn, Whisper, TurnMetric
from app.compliance.runner import run_compliance
from app.seed import seed_agents


async def seed():
    print("Initializing database...")
    init_engine()
    await create_all()

    async for session in get_session():
        await seed_agents(session)

        # Get first agent
        agents = (await session.execute(Agent.__table__.select())).fetchall()
        if not agents:
            print("No agents found.")
            return
        agent_id = agents[0].id
        print(f"Using Agent: {agents[0].name} ({agent_id})")

        call_id = "demo-call-8842"
        now = datetime.now(timezone.utc) - timedelta(minutes=5)

        # Remove previous demo call if present
        existing_call = await session.get(Call, call_id)
        if existing_call:
            await session.delete(existing_call)
            await session.commit()

        # 1. Create Call
        call = Call(
            id=call_id,
            agent_id=agent_id,
            room_name=f"call-{call_id}",
            status="active",
            started_at=now,
        )
        session.add(call)
        await session.commit()

        # 2. Add realistic turns (demonstrating recording disclosure, conversation, whisper, and no refund)
        sample_turns = [
            (
                0,
                "agent",
                "Hello, thanks for calling Acme Support! Please note this call is recorded for quality assurance. How can I help you?",
                now + timedelta(seconds=2),
                now + timedelta(seconds=7),
                False,
            ),
            (
                1,
                "user",
                "Hi, my internet connection has been dropping frequently since yesterday afternoon.",
                now + timedelta(seconds=8),
                now + timedelta(seconds=13),
                False,
            ),
            (
                2,
                "agent",
                "I completely understand how frustrating that is. Let me check the connection telemetry for your area right now.",
                now + timedelta(seconds=14),
                now + timedelta(seconds=19),
                False,
            ),
            (
                3,
                "user",
                "Okay, I was hoping to get a credit or refund on my monthly invoice for the downtime.",
                now + timedelta(seconds=20),
                now + timedelta(seconds=25),
                False,
            ),
            (
                4,
                "agent",
                "I can certainly review promotional options for your account, and I would be glad to offer you a 10% courtesy discount on your next bill while our team inspects the neighborhood line.",
                now + timedelta(seconds=26),
                now + timedelta(seconds=33),
                False,
            ),
            (
                5,
                "user",
                "That works, thank you! Let me restart the router as well.",
                now + timedelta(seconds=34),
                now + timedelta(seconds=38),
                False,
            ),
            (
                6,
                "agent",
                "Sounds great! Please keep an eye on the modem lights, and don't hesitate to reach back out if you need anything else.",
                now + timedelta(seconds=39),
                now + timedelta(seconds=45),
                True,  # User barged in to say thanks
            ),
        ]

        for idx, speaker, text, start, end, interrupted in sample_turns:
            turn = Turn(
                call_id=call_id,
                idx=idx,
                speaker=speaker,
                text=text,
                started_at=start,
                ended_at=end,
                interrupted=interrupted,
            )
            session.add(turn)

        # 3. Add whisper
        whisper = Whisper(
            call_id=call_id,
            text="Offer a 10% courtesy promotional discount on their next bill",
            sent_at=now + timedelta(seconds=24),
            applied_at_turn=4,
        )
        session.add(whisper)

        # 4. Add 5-stage latency metrics for agent turns (0, 2, 4, 6)
        metrics = [
            TurnMetric(
                call_id=call_id,
                turn_idx=0,
                vad_end_ms=0.0,
                stt_final_ms=0.0,
                llm_ttft_ms=92.0,
                tts_ttfb_ms=138.0,
                audio_published_ms=142.0,
                e2e_ms=230.0,
            ),
            TurnMetric(
                call_id=call_id,
                turn_idx=2,
                vad_end_ms=118.0,
                stt_final_ms=182.0,
                llm_ttft_ms=96.0,
                tts_ttfb_ms=144.0,
                audio_published_ms=149.0,
                e2e_ms=540.0,
            ),
            TurnMetric(
                call_id=call_id,
                turn_idx=4,
                vad_end_ms=124.0,
                stt_final_ms=179.0,
                llm_ttft_ms=104.0,
                tts_ttfb_ms=141.0,
                audio_published_ms=146.0,
                e2e_ms=548.0,
            ),
            TurnMetric(
                call_id=call_id,
                turn_idx=6,
                vad_end_ms=115.0,
                stt_final_ms=175.0,
                llm_ttft_ms=89.0,
                tts_ttfb_ms=132.0,
                audio_published_ms=136.0,
                e2e_ms=511.0,
            ),
        ]
        for m in metrics:
            session.add(m)

        await session.commit()

        # 5. Mark ended and run compliance
        call.status = "ended"
        call.ended_at = now + timedelta(seconds=46)
        await session.commit()

        print(f"Running compliance engine for {call_id}...")
        results = await run_compliance(call_id, session)
        print(f"Compliance evaluated: {[r.status for r in results]}")
        print("\nDemo call successfully seeded! Open http://localhost:3000/dashboard to view.")
        break


if __name__ == "__main__":
    asyncio.run(seed())
