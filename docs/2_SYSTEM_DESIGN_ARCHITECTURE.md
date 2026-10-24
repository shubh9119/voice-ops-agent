# Architecture 2: System Design & Component Architecture

> **Document Purpose:** Deep-dive technical system design covering the 4-tier decoupled architecture, network protocol topology, database schema, data channels, and component responsibilities.

---

## 1. Multi-Tier System Design Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              TIER 1: PRESENTATION & CLIENT TIER                         │
│                                                                                        │
│   Next.js 14 (App Router) + TypeScript + Tailwind CSS                                  │
│   ┌───────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────┐   │
│   │ Customer UI (/call/[id])  │  │ Supervisor (/operator/[id])│ │ Dashboard        │   │
│   │ - WebRTC Audio I/O        │  │ - Hidden Listener Mode    │  │ - Call History   │   │
│   │ - Live Subtitle Deltas    │  │ - Data-Channel Whisper    │  │ - Compliance Pass│   │
│   │ - Mic Controls & Mute     │  │ - Takeover Mic Publisher  │  │ - Latency Charts │   │
│   └─────────────┬─────────────┘  └─────────────┬─────────────┘  └────────┬─────────┘   │
└─────────────────┼──────────────────────────────┼─────────────────────────┼─────────────┘
                  │ WebRTC (RTP/RTCP + Data)     │ WebRTC (Listen + Data)  │ HTTP REST
                  ▼                              ▼                         │
┌──────────────────────────────────────────────────────────────────────────┼─────────────┐
│                              TIER 2: REAL-TIME MEDIA & ROUTING TIER      │             │
│                                                                          │             │
│   Self-Hosted LiveKit SFU (Selective Forwarding Unit)                     │             │
│   ┌──────────────────────────────────────────────────────────────────┐   │             │
│   │ Control Plane: TCP Port 7880 (REST API + WebSocket Signalling)   │   │             │
│   │ Media Plane:   UDP Ports 50000–60000 (RTP/RTCP Opus Voice Audio) │   │             │
│   │ Fallback:      TCP Port 7881 (ICE TCP for restrictive firewalls) │   │             │
│   │ NAT Traversal: UDP Port 3478 (Integrated STUN/TURN server)       │   │             │
│   │                                                                  │   │             │
│   │ Room State: "call-<id>"                                          │   │             │
│   │  ├─ Participant: customer (can_publish=True, can_subscribe=True) │   │             │
│   │  ├─ Participant: agent    (can_publish=True, can_subscribe=True) │   │             │
│   │  └─ Participant: operator (hidden=True, can_publish=True)        │   │             │
│   └──────────────────────────────────┬───────────────────────────────┘   │             │
└──────────────────────────────────────┼───────────────────────────────────┼─────────────┘
                                       │ WebRTC (RoomIO)                   │
                                       ▼                                   │
┌──────────────────────────────────────────────────────────────────────────┼─────────────┐
│                              TIER 3: VOICE INTELLIGENCE & WORKER TIER    │             │
│                                                                          │             │
│   Python LiveKit Agents Framework (`voiceagent.main`)                     │             │
│   ┌──────────────────────────────────────────────────────────────────┐   │             │
│   │ 1. Voice Activity Detection:  Silero VAD (pre-warmed in memory)  │   │             │
│   │ 2. Speech-to-Text (STT):      Deepgram Nova-3 (WebSocket Stream) │   │             │
│   │ 3. LLM Inference:             Groq Qwen3.8-27b (TTFT ~230ms)     │   │             │
│   │ 4. Text-to-Speech (TTS):      Deepgram Aura-2 (speed=0.92, 48kHz)│   │             │
│   │ 5. Turn Handling & Endpoint:  Local VAD (min: 0.2s, max: 1.8s)   │   │             │
│   │ 6. Barge-in / Interruption:   Dynamic utterance trimming         │   │             │
│   │ 7. Telemetry & Metrics:       5-Stage latency extraction         │   │             │
│   └──────────────────────────────────┬───────────────────────────────┘   │             │
└──────────────────────────────────────┼───────────────────────────────────┼─────────────┘
                                       │ Internal HTTP Telemetry (X-Key)   │
                                       ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              TIER 4: ORCHESTRATION & PERSISTENCE TIER                  │
│                                                                                        │
│   FastAPI Backend (`app.main:app`)                                                     │
│   ┌───────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────┐   │
│   │ Call Manager Router       │  │ Agent Catalog Router      │  │ Compliance Engine│   │
│   │ - POST /calls (Room+Disp) │  │ - CRUD /agents            │  │ - 30s Disclosure │   │
│   │ - POST /calls/{id}/op-tok │  │ - System Prompt & Catalog │  │ - Secrecy Guard  │   │
│   │ - GET /calls/{id}/metrics │  │ - Speed & Persona config  │  │ - LLM Refund Aud │   │
│   └─────────────┬─────────────┘  └─────────────┬─────────────┘  └────────┬─────────┘   │
│                 │                              │                         │             │
│                 └──────────────────────────────┼─────────────────────────┘             │
│                                                ▼                                       │
│   Database (SQLite / PostgreSQL via SQLAlchemy Async Engine)                           │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐   │
│   │ agents table │ │ calls table  │ │ turns table  │ │ turn_metrics │ │ compliance │   │
│   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component-by-Component Responsibilities

### Tier 1: Presentation & Frontend (Next.js 14)
- **Framework:** Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide icons.
- **WebRTC Client Engine:** `livekit-client` NPM package.
- **Audio Lifecycle Management:**
  - Listens to `RoomEvent.TrackSubscribed`. When an incoming audio track is detected, attaches it to an HTML5 `<audio>` element with `autoplay = true`.
  - Calls `room.startAudio()` immediately upon room connection to satisfy browser autoplay security policies.
- **Data Channels:**
  - `topic="transcript"`: Decodes JSON packets and renders streaming chat bubbles (gray for interim STT, solid for final turns, strikethrough for interrupted utterances).
  - `topic="whisper"`: Transmits private supervisor guidance targeted directly to the agent worker.
  - `topic="takeover"`: Signals `{action: "start"}` or `{action: "stop"}` to transfer microphone ownership.

---

### Tier 2: Real-Time Media & Routing (Self-Hosted LiveKit SFU)
- **Architecture:** Selective Forwarding Unit (SFU) written in Go.
- **Why SFU over MCU:**
  - **MCU (Multipoint Control Unit):** Decodes all participant audio streams, mixes them into a single audio track, and re-encodes. Introduces **150–300ms of audio latency** and consumes massive server CPU.
  - **SFU (Our Choice):** Acts as an intelligent RTP packet forwarder. It routes audio packets without transcoding or decoding, maintaining **sub-20ms network latency** and minimal CPU load.
- **Network Protocol & Port Map:**
  - `7880 TCP`: Signalling, SDP offer/answer exchange, ICE candidates, and HTTP room dispatch API.
  - `7881 TCP`: Fallback ICE TCP transport when UDP is blocked by corporate firewalls.
  - `50000–60000 UDP`: High-throughput RTP/RTCP transport for 20ms Opus voice frames.
  - `3478 UDP`: Integrated STUN/TURN server for NAT traversal.

---

### Tier 3: Voice Intelligence & Worker (Python LiveKit Agents)
- **Runtime:** Python 3.12 running `livekit-agents` v1.8+.
- **Pipeline Wiring:**
  - **VAD:** Silero VAD (pre-warmed once at process startup into `proc.userdata["vad"]`).
  - **STT:** Deepgram Nova-3 over WebSocket stream.
  - **LLM:** Groq Qwen3.8-27B (`temperature=0.3`, `max_completion_tokens=120`, TTFT ~230ms).
  - **TTS:** Deepgram Aura-2 (`aura-2-thalia-en`, `speed=0.92`, 48kHz PCM).
- **Turn Detection & Endpointing:**
  - Configured with `turn_detection='vad'`, `min_endpointing_delay=0.2s`, `max_endpointing_delay=1.8s`.
  - Operates completely locally without relying on external cloud barge-in gateways.
- **Interruption / Barge-in Trimming:**
  - When customer speech is detected while the agent is speaking, the worker cancels the TTS audio emitter in <100ms.
  - It automatically truncates the assistant's `ChatMessage.text_content` in conversation history to only the exact words delivered, flagging `interrupted=True`.

---

### Tier 4: Orchestration & Data Persistence (FastAPI)
- **Framework:** FastAPI with async SQLAlchemy and Pydantic v2 schemas.
- **Database Schema:**
  1. `agents`: id, name, system_prompt, greeting, voice, model.
  2. `calls`: id, agent_id, room_name, status (`waiting`, `active`, `ended`), started_at, ended_at.
  3. `turns`: id, call_id, idx, speaker (`user` | `agent`), text, started_at, ended_at, interrupted.
  4. `turn_metrics`: id, call_id, turn_idx, vad_end_ms, stt_final_ms, llm_ttft_ms, tts_ttfb_ms, e2e_ms.
  5. `compliance_results`: id, call_id, rule, method (`deterministic` | `llm`), status (`pass` | `fail`), offending_line, detail.
  6. `whispers`: id, call_id, text, sent_at, applied_at_turn.
- **Token Minting Security:**
  - **Customer Token:** `can_publish=True, can_subscribe=True, can_publish_data=False`.
  - **Operator Token:** `hidden=True, can_publish=True, can_subscribe=True, can_publish_data=True`.

---

## 3. Communication Protocols & Data Flow Matrix

| Interaction | Protocol | Latency | Payload / Format |
| :--- | :--- | :---: | :--- |
| **Browser ↔ LiveKit Signalling** | WebSocket (TCP 7880) | 10–30 ms | JSON (SDP Offers, Answers, ICE Candidates) |
| **Browser ↔ LiveKit Media** | WebRTC / RTP (UDP 50k-60k) | 15–40 ms | Opus Audio (20ms frames, 16kHz–48kHz) |
| **Browser ↔ Worker Transcripts** | WebRTC Data Channel | 10–25 ms | JSON (`{type: "transcript", text, is_final}`) |
| **Operator ↔ Worker Whisper** | WebRTC Data Channel | 10–25 ms | JSON (`{type: "whisper", text: "..."}`) |
| **Worker ↔ Deepgram STT** | Secure WebSocket (WSS) | 80–180 ms | Raw PCM audio stream → JSON transcription |
| **Worker ↔ Groq LLM** | HTTP/2 Streaming (REST) | 200–250 ms | SSE (Server-Sent Events) token stream |
| **Worker ↔ Deepgram TTS** | Secure WebSocket (WSS) | 300–360 ms | Text tokens in → 48kHz linear16 audio out |
| **Worker ↔ FastAPI Backend** | HTTP/1.1 REST (`X-Key`) | 2–5 ms | JSON batch reports (turns, metrics, status) |
