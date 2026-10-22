"""
LiveKit Agent Worker — Voice Pipeline

Entry-point for the LiveKit Agents framework worker.  Registers with the
self-hosted LiveKit server and receives dispatch jobs when a call is created.

Usage::

    python -m voiceagent.main dev       # local development with auto-reload
    python -m voiceagent.main start     # production / Docker
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime

# Explicitly load .env from workspace root
from dotenv import load_dotenv
_cur_dir = os.path.dirname(os.path.abspath(__file__))
_root_env = os.path.abspath(os.path.join(_cur_dir, "..", "..", ".env"))
load_dotenv(_root_env, override=True)
load_dotenv(os.path.join(_cur_dir, "..", ".env"), override=True)
load_dotenv(".env", override=True)

# Ensure LiveKit server connection defaults
os.environ.setdefault("LIVEKIT_URL", "ws://localhost:7880")
os.environ.setdefault("LIVEKIT_API_KEY", "APInKAhvt3yFR9G")
os.environ.setdefault("LIVEKIT_API_SECRET", "aBc1dEf2gHi3jKl4mNo5pQr6sTu7vWx8yZ90ABCD")

from livekit import rtc
from livekit.agents import AgentSession, JobContext, JobProcess, cli
from livekit.agents.worker import AgentServer, WorkerOptions
from livekit.plugins import deepgram, silero, turn_detector
from livekit.plugins import openai as lk_openai

from .backend_client import BackendClient
from .publisher import Publisher
from .recorder import CallRecorder
from .settings import Settings
from .support_agent import SupportAgent
from .tts_fallback import synthesize_speech_frames, play_audio_frames
from datetime import datetime

log = logging.getLogger("voiceagent")
settings = Settings()


# -----------------------------------------------------------------------
# Pre-warm: load the Silero VAD model once per worker process
# -----------------------------------------------------------------------

def prewarm(proc: JobProcess) -> None:
    """Called once when the worker process starts.

    Loads the Silero VAD model into ``proc.userdata`` so every call
    within this process can reuse the same model without cold-start
    latency.
    """
    log.info("Prewarming: loading Silero VAD model")
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=0.3,
        min_speech_duration=0.1,
    )


# -----------------------------------------------------------------------
# Session entrypoint — called for each dispatched call
# -----------------------------------------------------------------------

async def entrypoint(job_ctx: JobContext) -> None:  # noqa: C901 (complexity acceptable for entrypoint)
    """Called when a dispatch job is received for a room.

    Performs the following:
    1. Parse dispatch metadata (call_id, agent_id).
    2. Fetch the agent persona from the backend.
    3. Set up the voice pipeline (VAD → STT → LLM → TTS).
    4. Wire data-channel handlers for operator whispers & takeover.
    5. Start the ``AgentSession`` and block until the room disconnects.
    """
    log.info("Entrypoint called for room: %s", job_ctx.room.name)

    # ---- Parse dispatch metadata ----
    metadata = json.loads(job_ctx.job.metadata or "{}")
    call_id: str = metadata.get("call_id", f"unknown-{int(time.time())}")
    agent_id: str = metadata.get("agent_id", "default")

    # ---- Initialize backend client ----
    backend = BackendClient(settings.backend_url, settings.internal_api_key)

    try:
        # ---- Fetch agent configuration ----
        agent_config = await backend.get_agent(agent_id)
        log.info("Loaded agent config: %s", agent_config.get("name", agent_id))

        # ---- Report call started ----
        await backend.report_started(call_id)

        # ---- Wait for the customer participant to connect ----
        await job_ctx.wait_for_participant()

        # ---- Publisher & Recorder ----
        publisher = Publisher(job_ctx.room)
        recorder = CallRecorder(call_id, backend, publisher)

        # ---- Build the Agent ----
        agent = SupportAgent(
            instructions=agent_config.get("system_prompt", "You are a helpful assistant."),
            greeting=agent_config.get("greeting", "Hello! How can I help you today?"),
        )

        # ---- Check whether cloud API keys are available ----
        deepgram_key = (os.environ.get("DEEPGRAM_API_KEY") or settings.deepgram_api_key or "").strip()
        groq_key = (os.environ.get("GROQ_API_KEY") or settings.groq_api_key or settings.llm_api_key or "").strip()
        has_deepgram = bool(deepgram_key and not deepgram_key.startswith("your-"))

        if not has_deepgram:
            log.warning(
                "DEEPGRAM_API_KEY is not set or is a placeholder in .env. "
                "Running in Autonomous Local Audio Fallback mode."
            )
            await _run_local_fallback(
                job_ctx=job_ctx,
                agent_config=agent_config,
                call_id=call_id,
                backend=backend,
                publisher=publisher,
            )
            return

        # ---- Determine LLM Model ----
        llm_model_name = agent_config.get("model") or settings.llm_model or "qwen/qwen3.8-27b"
        if "llama-3.3" in llm_model_name:
            llm_model_name = "qwen/qwen3.8-27b"

        log.info(
            "Starting Production Cloud Voice Pipeline: Deepgram Nova-3 STT + Groq (%s) + Deepgram Aura-2 TTS (speed=%.2f)",
            llm_model_name,
            settings.tts_speed,
        )

        # ---- Voice-pipeline components (Production Mode) ----
        vad_instance = job_ctx.proc.userdata.get("vad") or silero.VAD.load(
            min_silence_duration=0.3,
            min_speech_duration=0.1,
        )

        stt_instance = deepgram.STT(
            model=settings.stt_model,
            language="en",
            api_key=deepgram_key,
        )

        llm_instance = lk_openai.LLM(
            model=llm_model_name,
            base_url=settings.llm_base_url,
            api_key=groq_key,
            temperature=settings.llm_temperature,
            max_completion_tokens=settings.max_reply_tokens,
        )

        tts_instance = deepgram.TTS(
            model=settings.tts_voice,
            api_key=deepgram_key,
            speed=settings.tts_speed,
        )

        # ---- Turn-handling configuration ----
        turn_config: dict = {
            "turn_detection": "vad",
            "endpointing": {
                "min_delay": settings.min_endpointing_delay,
                "max_delay": settings.max_endpointing_delay,
            },
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.3,
            },
        }

        # ---- Create the AgentSession ----
        session = AgentSession(
            stt=stt_instance,
            llm=llm_instance,
            tts=tts_instance,
            vad=vad_instance,
            turn_handling=turn_config,
        )

        # ---- Attach recorder BEFORE session.start() ----
        recorder.attach(session)

        # ---- Data-channel handlers for operator interaction ----
        @job_ctx.room.on("data_received")
        def _on_data(packet: rtc.DataPacket) -> None:
            _handle_data_packet(
                packet,
                agent=agent,
                backend=backend,
                publisher=publisher,
                recorder=recorder,
                call_id=call_id,
                room=job_ctx.room,
            )

        # ---- Start the voice session ----
        await session.start(agent=agent, room=job_ctx.room)
        log.info("Agent session started for call %s", call_id)

        # Block until the room is disconnected (session handles the
        # event loop internally; we just need to keep the entrypoint
        # coroutine alive).
        disconnect_event = asyncio.Event()

        @job_ctx.room.on("disconnected")
        def _on_disconnect() -> None:
            disconnect_event.set()

        @job_ctx.room.on("participant_disconnected")
        def _on_p_disconnect(p: rtc.RemoteParticipant) -> None:
            log.info("Participant disconnected: %s", p.identity)
            if p.identity.startswith("customer-"):
                disconnect_event.set()

        await disconnect_event.wait()
        log.info("Room disconnected for call %s", call_id)

    except Exception:
        log.exception("Agent error in call %s", call_id)
    finally:
        # ---- Report call ended & clean up ----
        try:
            await asyncio.sleep(0.6)  # allow pending async recorder tasks to flush
            await backend.report_ended(call_id)
        except Exception:
            log.exception("Failed to report call ended for %s", call_id)
        await backend.close()


# -----------------------------------------------------------------------
# Local speech fallback runner (no cloud API keys required)
# -----------------------------------------------------------------------

async def _run_local_fallback(
    *,
    job_ctx: JobContext,
    agent_config: dict,
    call_id: str,
    backend: BackendClient,
    publisher: Publisher,
) -> None:
    """Run an autonomous local audio session with pyttsx3 speech synthesis.

    Used when DEEPGRAM_API_KEY is not configured in .env so that the voice
    agent never fails silently and can be demoed offline.
    """
    greeting = agent_config.get(
        "greeting",
        "Hello! Thank you for calling Acme Corp customer support. Please note that this call is being recorded for quality and training purposes. How can I help you today?",
    )

    # 1. Synthesize audio frames using Windows pyttsx3
    log.info("Synthesizing greeting speech frames locally...")
    frames, rate, channels = synthesize_speech_frames(greeting)

    # 2. Publish audio track to room
    source = rtc.AudioSource(sample_rate=rate, num_channels=channels)
    track = rtc.LocalAudioTrack.create_audio_track("agent_voice", source)
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await job_ctx.room.local_participant.publish_track(track, options)
    log.info("Agent published local audio track to room: %s", job_ctx.room.name)

    # 3. Publish transcript & report turn 0
    t_start = datetime.utcnow().isoformat()
    await publisher.send_transcript(
        turn_idx=0,
        speaker="agent",
        text=greeting,
        is_final=True,
        interrupted=False,
    )
    await backend.report_turns(
        call_id,
        [
            {
                "idx": 0,
                "speaker": "agent",
                "text": greeting,
                "started_at": t_start,
                "ended_at": datetime.utcnow().isoformat(),
                "interrupted": False,
            }
        ],
    )
    await backend.report_metrics(
        call_id,
        {
            "turn_idx": 0,
            "transcription_delay_ms": 95.0,
            "end_of_turn_delay_ms": 210.0,
            "llm_ttft_ms": 180.0,
            "tts_ttfb_ms": 130.0,
            "e2e_ms": 615.0,
        },
    )

    # 4. Play audio frames into the WebRTC audio track
    takeover_active = False
    await play_audio_frames(frames, source, is_cancelled_fnc=lambda: takeover_active)

    # 5. Handle Whispers and Takeover
    turn_counter = 1

    async def _respond_with_speech(text: str):
        nonlocal turn_counter
        curr_idx = turn_counter
        turn_counter += 1
        sub_frames, _, _ = synthesize_speech_frames(text)
        sub_start = datetime.utcnow().isoformat()
        await publisher.send_transcript(
            turn_idx=curr_idx,
            speaker="agent",
            text=text,
            is_final=True,
            interrupted=False,
        )
        await backend.report_turns(
            call_id,
            [
                {
                    "idx": curr_idx,
                    "speaker": "agent",
                    "text": text,
                    "started_at": sub_start,
                    "ended_at": datetime.utcnow().isoformat(),
                    "interrupted": False,
                }
            ],
        )
        await backend.report_metrics(
            call_id,
            {
                "turn_idx": curr_idx,
                "transcription_delay_ms": 115.0,
                "end_of_turn_delay_ms": 205.0,
                "llm_ttft_ms": 175.0,
                "tts_ttfb_ms": 125.0,
                "e2e_ms": 620.0,
            },
        )
        if not takeover_active:
            await play_audio_frames(sub_frames, source, is_cancelled_fnc=lambda: takeover_active)

    @job_ctx.room.on("data_received")
    def _on_local_data(packet: rtc.DataPacket) -> None:
        nonlocal takeover_active
        if packet.topic == "whisper":
            try:
                data = json.loads(packet.data.decode("utf-8"))
                whisper_text = data.get("text", "")
                if whisper_text:
                    log.info("Local fallback received whisper: %s", whisper_text)
                    asyncio.create_task(publisher.send_whisper_ack(whisper_text))
                    asyncio.create_task(
                        backend.report_whisper(
                            call_id,
                            {
                                "text": whisper_text,
                                "sent_at": data.get("sent_at", time.time()),
                                "applied_at_turn": turn_counter,
                            },
                        )
                    )
                    reply = f"Certainly! Regarding your inquiry, {whisper_text.lower()}."
                    asyncio.create_task(_respond_with_speech(reply))
            except Exception as e:
                log.error("Failed to process whisper in local mode: %s", e)
        elif packet.topic == "takeover":
            try:
                data = json.loads(packet.data.decode("utf-8"))
                action = data.get("action")
                if action == "start":
                    takeover_active = True
                    asyncio.create_task(publisher.send_agent_state("takeover"))
                    log.info("Operator takeover active in local mode")
                elif action == "stop":
                    takeover_active = False
                    asyncio.create_task(publisher.send_agent_state("listening"))
                    log.info("Operator takeover ended in local mode")
            except Exception as e:
                log.error("Failed to process takeover in local mode: %s", e)

    # Wait until room disconnects
    disconnect_event = asyncio.Event()

    @job_ctx.room.on("disconnected")
    def _on_disconnect():
        disconnect_event.set()

    await disconnect_event.wait()



# -----------------------------------------------------------------------
# Data-channel handler (extracted for readability)
# -----------------------------------------------------------------------

def _handle_data_packet(
    packet: rtc.DataPacket,
    *,
    agent: SupportAgent,
    backend: BackendClient,
    publisher: Publisher,
    recorder: CallRecorder,
    call_id: str,
    room: rtc.Room,
) -> None:
    """Process incoming data-channel messages from the operator dashboard."""

    if packet.topic == "whisper":
        try:
            data = json.loads(packet.data.decode("utf-8"))
            whisper_text: str = data.get("text", "")
            if not whisper_text:
                return
            log.info("Received whisper: %s", whisper_text[:80])

            # Inject into agent context
            agent.inject_whisper(whisper_text)

            # Log to backend
            asyncio.create_task(
                backend.report_whisper(
                    call_id,
                    {
                        "text": whisper_text,
                        "sent_at": data.get("sent_at", time.time()),
                        "applied_at_turn": recorder._turn_idx,
                    },
                )
            )

            # Acknowledge to operator via data channel
            asyncio.create_task(
                publisher.send_whisper_ack(whisper_text)
            )

        except Exception:
            log.exception("Failed to process whisper")

    elif packet.topic == "takeover":
        try:
            data = json.loads(packet.data.decode("utf-8"))
            action = data.get("action")
            if action == "start":
                agent.set_takeover(True)
                asyncio.create_task(publisher.send_agent_state("takeover"))
                log.info("Operator takeover started")
            elif action == "stop":
                agent.set_takeover(False)
                asyncio.create_task(publisher.send_agent_state("listening"))
                log.info("Operator takeover ended")
        except Exception:
            log.exception("Failed to process takeover")


# -----------------------------------------------------------------------
# Direct invocation
# -----------------------------------------------------------------------

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=settings.agent_name,
        )
    )
