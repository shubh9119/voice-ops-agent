# VoiceOps — Operator-Guided Voice AI Agent

> Production-grade voice AI agent platform on self-hosted LiveKit with real-time operator controls, compliance checking, and latency analytics.

[![LiveKit](https://img.shields.io/badge/LiveKit-SFU_Self--Hosted-blue?logo=livekit)](https://livekit.io)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_14_App_Router-black?logo=next.js)](https://nextjs.org)
[![Deepgram](https://img.shields.io/badge/STT%20%26%20TTS-Deepgram_Nova--3_%26_Aura--2-purple)](https://deepgram.com)
[![Groq](https://img.shields.io/badge/LLM-Groq_Qwen3.8--27B-orange)](https://groq.com)

---

> 🎥 **Demo Video:** [Watch Video Walkthrough (Loom / YouTube) — *link to be updated*]  
> 📦 **GitHub Repository:** [https://github.com/shubh9119/voice-ops-agent](https://github.com/shubh9119/voice-ops-agent)

---

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Option 1: Docker Compose](#option-1-docker-compose-recommended)
  - [Option 2: Native / Local Development](#option-2-native--local-development)
- [Self-Hosted LiveKit — Ports & Config](#self-hosted-livekit--ports--config)
- [Project Structure](#project-structure)
- [Part-by-Part Implementation Breakdown](#part-by-part-breakdown)
  - [Part A — Self-Hosted LiveKit](#part-a--self-hosted-livekit-)
  - [Part B — Voice Agent Pipeline & Barge-In](#part-b--voice-agent-)
  - [Part C — FastAPI Backend & Dispatch](#part-c--backend-api-)
  - [Part D — Next.js 14 Web Client](#part-d--web-client-)
  - [Part E — Operator Panel (Whisper & Takeover)](#part-e--operator-)
  - [Part F — Compliance Engine (Deterministic & LLM)](#part-f--compliance-)
  - [Part G — Latency Measurements & Waterfall](#part-g--latency-)
- [Stretch Goals Implemented](#stretch-goals-implemented)
- [Review Call Preparation](#review-call-preparation)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Browser (Next.js 14)                         │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Home   │  │  /call/[id]  │  │ /operator/[id]│ │  Dashboard   │   │
│  │  Page   │  │  Customer    │  │  Hidden       │  │  Analytics  │   │
│  │         │  │  WebRTC      │  │  WebRTC       │  │  & Audit    │   │
│  └─────────┘  └──────┬───────┘  └──────┬────────┘  └──────────────┘   │
│                       │ audio           │ audio (listen-only)        │
│                       │ data            │ data (whisper/takeover)     │
└───────────────────────┼─────────────────┼────────────────────────────┘
                        │                 │
                   ┌────▼─────────────────▼────┐
                   │   Self-Hosted LiveKit SFU  │
                   │   (Selective Forwarding)   │
                   │                            │
                   │  Room "call-<id>"          │
                   │  ├─ customer (publish+sub) │
                   │  ├─ agent (publish+sub)    │
                   │  └─ operator (hidden, sub) │
                   └─────────────┬──────────────┘
                                 │ WebRTC
                   ┌─────────────▼──────────────┐
                   │   Agent Worker (Python)     │
                   │                             │
                   │  Silero VAD                 │
                   │  → Deepgram STT (nova-3)    │
                   │  → Groq LLM (qwen3.8-27b)   │
                   │  → Deepgram TTS (aura-2)    │
                   │                             │
                   │  + Whisper injection         │
                   │  + Takeover handling         │
                   │  + Transcript publishing     │
                   │  + Latency metrics waterfall │
                   └─────────────┬──────────────┘
                                 │ HTTP
                   ┌─────────────▼──────────────┐
                   │   FastAPI Backend           │
                   │                             │
                   │  POST/GET /agents           │
                   │  POST/GET /calls            │
                   │  POST /calls/{id}/operator  │
                   │                             │
                   │  Compliance Engine:          │
                   │  ├─ Recording disclosure     │
                   │  │   (deterministic, <30s)   │
                   │  ├─ Secret supervisor check  │
                   │  │   (deterministic)         │
                   │  └─ No refund promise        │
                   │      (LLM, structured JSON)  │
                   │                             │
                   │  SQLite / PostgreSQL        │
                   └─────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- **Docker** & **Docker Compose** (v2+) OR **Python 3.11+** & **Node.js 18+**
- Free-tier API keys:
  - [Deepgram](https://console.deepgram.com) — STT (`nova-3`) & TTS (`aura-2-thalia-en`)
  - [Groq](https://console.groq.com) — Ultra-fast LLM inference (`qwen/qwen3.8-27b`)
  - [OpenAI](https://platform.openai.com) — Optional for compliance check (defaults automatically to Groq if absent)

### Option 1: Docker Compose (recommended)

```bash
# 1. Clone and configure
git clone https://github.com/shubh9119/voice-ops-agent.git
cd voice-ops-agent
cp .env.example .env
# Edit .env with your DEEPGRAM_API_KEY and GROQ_API_KEY

# 2. Start full stack (LiveKit + Backend + 2 Worker Replicas + Next.js)
docker compose up --build

# 3. Open browser
#    Customer & Operator UI:  http://localhost:3000
#    Backend API & Swagger:   http://localhost:8000/docs
```

### Option 2: Native / Local Development

```bash
# 1. Configure environment
cp .env.example .env

# Terminal 1: LiveKit Server (Windows native executable or Docker)
# Windows:
./infra/livekit-server.exe --config ./infra/livekit.yaml
# Linux/macOS:
docker run --rm -p 7880:7880 -p 7881:7881 -p 50000-50100:50000-50100/udp \
  -v $(pwd)/infra/livekit.yaml:/etc/livekit.yaml \
  livekit/livekit-server:v1.8 --config /etc/livekit.yaml

# Terminal 2: FastAPI Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload

# Terminal 3: LiveKit Agent Worker
cd agent
pip install -r requirements.txt
python -m voiceagent.main dev

# Terminal 4: Next.js Frontend
cd web
npm install
npm run dev   # or npm run build && npm run start
```

---

## Self-Hosted LiveKit — Ports & Config

| Port | Protocol | Purpose |
|------|----------|---------|
| **7880** | TCP | **HTTP + WebSocket Signalling.** Used for room creation REST API, agent worker dispatch, participant auth JWT verification, and initial WebRTC SDP offer/answer/ICE candidate exchange. No media flows through this port. |
| **7881** | TCP | **TCP Media Fallback.** When restrictive corporate firewalls or NATs block UDP traffic, WebRTC falls back to ICE TCP candidates on this port. |
| **50000–60000** | UDP | **RTP/RTCP Media Transport.** High-throughput UDP transport for Opus voice audio packets. UDP avoids TCP head-of-line blocking so dropped packets are seamlessly concealed by the Opus PLC (Packet Loss Concealment) decoder. |
| **3478** | UDP | **STUN / TURN Server.** Built-in STUN resolves the client's public IP (server-reflexive candidate); TURN relays media packets when symmetric NATs prevent direct peer-to-SFU connections. |

### Config file: `infra/livekit.yaml`

```yaml
port: 7880
bind_addresses:
  - "0.0.0.0"
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: false
turn:
  enabled: true
  udp_port: 3478
keys:
  APInKAhvt3yFR9G: aBc1dEf2gHi3jKl4mNo5pQr6sTu7vWx8yZ90ABCD
```

---

## Project Structure

```
.
├── docker-compose.yml          # Full-stack Docker orchestration
├── .env.example                # Environment configuration template
├── infra/
│   ├── livekit.yaml            # LiveKit server configuration
│   └── livekit-server.exe      # Windows native LiveKit SFU server binary
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # App factory, CORS, lifespan seeding
│   │   ├── config.py           # Pydantic settings from .env
│   │   ├── db.py               # Async SQLAlchemy engine + sessionmaker
│   │   ├── models.py           # ORM: Agent, Call, Turn, TurnMetric, ComplianceResult
│   │   ├── schemas.py          # Pydantic validation schemas
│   │   ├── seed.py             # Pre-seeded agent personas with full product catalog
│   │   ├── routers/
│   │   │   ├── agents.py       # CRUD /agents
│   │   │   ├── calls.py        # /calls room create, token issuance, agent dispatch
│   │   │   └── internal.py     # /internal authenticated agent-worker telemetry
│   │   └── compliance/
│   │       ├── deterministic.py # Rule 1 (30s disclosure) & Rule 2 (operator secrecy)
│   │       ├── llm_check.py     # Rule 3 (no refund promise via structured LLM)
│   │       └── runner.py        # Orchestrates compliance evaluation upon call end
│   └── tests/
│       ├── test_compliance.py  # Unit tests for deterministic rules
│       └── test_api.py         # End-to-end API route tests
├── agent/                      # LiveKit Agent Worker
│   ├── Dockerfile
│   ├── requirements.txt
│   └── voiceagent/
│       ├── main.py             # Worker entrypoint, VAD, STT, LLM, TTS setup
│       ├── settings.py         # Worker settings (speech speed, models, delays)
│       ├── support_agent.py    # Custom SupportAgent with whisper & takeover hooks
│       ├── recorder.py         # Session events → transcript deltas + metrics
│       ├── backend_client.py   # Async HTTP client reporting to backend
│       ├── publisher.py        # WebRTC data channel publisher
│       └── latency.py          # Metrics extractor for the 5-stage latency waterfall
├── web/                        # Next.js 14 App Router dashboard
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx        # Home: agent directory, start customer call
│       │   ├── call/[id]/      # Customer WebRTC voice call with live transcript
│       │   ├── operator/[id]/  # Hidden operator: listen, whisper, take over
│       │   └── dashboard/      # History, compliance badges, latency waterfall charts
│       ├── components/         # Transcript, WhisperPanel, LatencyChart, AudioVisualizer
│       ├── lib/api.ts          # Type-safe backend client
│       └── types/index.ts      # Shared TypeScript definitions
└── scripts/
    ├── test_call_flow.py       # Automated LiveKit call dispatch verification
    └── test_two_way_convo.py   # Automated 2-way synthetic speech conversation test
```

---

## Part-by-Part Implementation Breakdown

### Part A — Self-Hosted LiveKit ✅
- Runs on custom configuration `infra/livekit.yaml` with pre-shared API key and secret.
- No LiveKit Cloud dependency.
- Correctly advertises ports and supports both UDP media and TCP fallback.

### Part B — Voice Agent & Interruption Handling ✅
- **Pipeline:** Silero VAD &rarr; Deepgram Nova-3 STT &rarr; Groq Qwen3.8-27B LLM &rarr; Deepgram Aura-2 TTS (`speed=0.92`).
- **Pre-warming:** Silero VAD model is pre-loaded once into process memory at worker startup (`prewarm_fnc`) to eliminate per-call cold starts.
- **Local VAD Turn Detection & Endpointing:** `turn_detection='vad'`, `min_endpointing_delay=0.2s`, `max_endpointing_delay=1.8s`.
- **Barge-In / Interruption Handling:** Real-time interruption detection stops TTS playback immediately when the user speaks. The session trims `ChatMessage.text_content` to what was actually delivered and sets `interrupted=True`.
- **System Prompt & Catalog:** Seeded persona includes Acme Corp's product catalog (Acme Smart Widget $99, Acme Cloud Pro $29/mo, Acme Home Hub $149, shipping policies, and 30-day return policy).

### Part C — Backend API ✅
- FastAPI with async SQLite/PostgreSQL.
- `POST /calls` creates a LiveKit room, issues participant tokens with appropriate grants, and dispatches an agent worker.
- `POST /calls/{id}/operator-token` generates an operator token with `hidden=True` and `can_publish=True`.
- `POST /internal/*` endpoints receive real-time turns, latency metrics, whispers, and call status events with internal API key auth.

### Part D — Web Client ✅
- Next.js 14 App Router, TypeScript, and Tailwind CSS.
- Real-time bidirectional WebRTC audio powered by `livekit-client`.
- Live transcript streaming via WebRTC data channel (`topic="transcript"`).
- Chat bubble view showing speaker labels, interim streaming text, final turns, and strikethrough styling for interrupted turns.

### Part E — Operator Controls (Whisper & Takeover) ✅
- **Hidden Participant:** Operator joins the room with `hidden=True`. The customer client never sees the operator in participant lists.
- **Private Whisper:** Operator types or clicks preset whisper suggestions (e.g. *"Offer 10% discount"*). Sent via reliable data channel directly to the agent.
- **Secrecy Protocol:** The agent injects the whisper as a system prompt instruction, incorporates it naturally into its speech, and never mentions the supervisor or operator.
- **Take Over & Hand Back:** Operator clicks **Take Over Call** &rarr; sends takeover event &rarr; agent mutes audio and pauses replies &rarr; operator speaks directly over microphone. Clicking **Hand Back** restores agent speaking mode.

### Part F — Compliance Engine ✅
1. **Rule 1: Recording Disclosure (< 30s) — Deterministic:**
   Checks agent utterances within the first 30 seconds of `call.started_at` for regex `/\brecord(ed|ing|s)?\b/i`. Pure deterministic evaluation.
2. **Rule 2: Operator Secrecy — Deterministic:**
   Guarantees the agent never leaks supervisor presence or internal words (`"operator"`, `"supervisor"`, `"whisper"`, `"instruction"`, `"behind the scenes"`).
3. **Rule 3: No Refund Promise — LLM Structured Audit:**
   Groq/OpenAI evaluates the transcript using JSON schema output (`passed: bool`, `offending_line: str`, `reason: str`). Verifies that the agent did not guarantee an unauthorized refund, with retry logic and transcript citation verification.

### Part G — Latency Measurements & Waterfall ✅

Each conversation turn records timing across the 5 distinct pipeline stages:

| Stage | Field | What It Measures |
|-------|-------|-----------------|
| 1. User stops &rarr; STT final | `stt_final_ms` | Deepgram Nova-3 real-time audio transcription delay |
| 2. STT final &rarr; Turn decision | `vad_end_ms` | Silero VAD endpointing & turn boundary detection |
| 3. Turn decision &rarr; LLM first token | `llm_ttft_ms` | Groq Qwen3.8-27b inference Time-To-First-Token |
| 4. LLM token &rarr; TTS first audio | `tts_node_ttfb` | Deepgram Aura-2 streaming Time-To-First-Byte |
| **5. Total End-to-End** | **`e2e_ms`** | **Total user speech end &rarr; agent voice heard** |

#### Verified Live Latency Benchmark (from automated test run):
```
Turn: "What products do you offer?"
- LLM Time-To-First-Token (TTFT):  230.73 ms
- TTS Time-To-First-Byte (TTFB):   359.78 ms
- Total End-to-End Voice Latency: 1,170.09 ms (~1.17 seconds)
```

---

## Stretch Goals Implemented

- [x] **Full `docker compose up` orchestration:** Spins up LiveKit SFU, FastAPI backend, 2 Agent Worker replicas, and Next.js frontend in one command.
- [x] **Operator Takeover & Hand-Back:** Seamless audio track management allowing supervisor to take over call audio and return control to the AI.
- [x] **Live Two-Way Conversation Automated Test:** Executable script (`python scripts/test_two_way_convo.py`) testing simulated speech capture, VAD endpointing, STT, LLM reasoning, TTS delivery, and compliance recording.

---

## Review Call Preparation

### 1. SFU vs MCU Architecture
- **SFU (Selective Forwarding Unit):** LiveKit receives audio/video tracks and forwards them to subscribers without decoding, transcoding, or mixing. This keeps server CPU minimal and enables sub-50ms latency.
- **MCU (Multipoint Control Unit):** Decodes and mixes all participant audio into a single stream. High server CPU cost and introduces 150-300ms of mixing delay. LiveKit's SFU architecture allows the agent worker to receive the customer's raw Opus stream directly.

### 2. LiveKit Dispatch Model
Agent workers register with the LiveKit server over WebSocket signalling (`agent_name="support-agent"`). When a call is created, the backend calls `CreateAgentDispatchRequest`. The server assigns the job to an available worker. The worker's `entrypoint` receives a `JobContext`, connects to the room, wires audio I/O via `RoomIO`, and manages the conversational state.

### 3. Scaling to 10,000 Concurrent Calls
- **LiveKit Server Clustering:** Deploy LiveKit SFUs behind a load balancer with a Redis cluster for room routing and participant state.
- **Worker Scaling:** Voice agent workers are CPU-bound on VAD and audio frame encoding. Deploy worker pods on Kubernetes using KEDA (Kubernetes Event-driven Autoscaling) scaling on pending LiveKit dispatch jobs.
- **Provider Concurrency:** Groq handles thousands of tokens/sec with sub-second TTFT. Deepgram streaming WebSocket connections support massive concurrent streaming audio sessions.
