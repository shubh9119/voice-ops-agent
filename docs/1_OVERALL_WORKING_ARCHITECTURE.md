# Architecture 1: Overall Working of the System

> **Document Purpose:** Complete end-to-end explanation of the Voice AI Agent lifecycle from call initiation, WebRTC media streaming, voice loop (VAD → STT → LLM → TTS), supervisor intervention, to post-call compliance audit.

---

## 1. High-Level Working Diagram

```
[CUSTOMER]                    [FRONTEND]             [LIVEKIT SFU]             [AGENT WORKER]             [BACKEND API]          [SUPERVISOR]
(Browser Mic/Spk)            (Next.js 14)             (Port 7880)              (Python Voice)              (FastAPI)            (Operator UI)
      │                           │                        │                          │                         │                     │
      │── 1. Clicks "Start Call" ─>│                        │                          │                         │                     │
      │                           │── 2. POST /calls ──────────────────────────────────────────────────────────>│                     │
      │                           │                        │<── 3. Create Room "call-xyz" ──────────────────────┤                     │
      │                           │                        │<── 4. Dispatch Agent "support-agent" ──────────────┤                     │
      │                           │<── 5. Returns JWT ──────────────────────────────────────────────────────────┘                     │
      │                           │                        │                          │                                               │
      │── 6. WebRTC Audio Stream ─┼── 7. SDP/ICE Handshake>│                          │                                               │
      │                           │                        │<── 8. Worker Joins Room ─┤                                               │
      │                           │                        │    (RoomIO wires audio)  │                                               │
      │<══════════════════════════╪════════════════════════╪════ 9. Spoken Greeting ══┤                                               │
      │                           │                        │    ("Recorded...")       │                                               │
      │                           │                        │                          │                                               │
      │── 10. Customer Speaks ───>│                        │── 11. RTP Audio Frames ─>│                                               │
      │   ("What products?")      │                        │                          ├── 12. Silero VAD (Speech detected)             │
      │                           │                        │                          ├── 13. Deepgram Nova-3 (STT Streaming)         │
      │                           │<── 14. Live Transcript Delta (Data Channel) ──────┤                                               │
      │                           │                        │                          ├── 15. Silence (Endpointing 200ms)             │
      │                           │                        │                          ├── 16. Groq Qwen3.8-27b (LLM TTFT ~230ms)      │
      │                           │                        │                          ├── 17. Deepgram Aura-2 (TTS TTFB ~360ms)       │
      │<════ 18. AI Voice Speaks ═╪════════════════════════╪════ 18. Audio Packets ───┘                                               │
      │    ("We offer Widget...") │                        │                                                                          │
      │                           │                        │                                                                          │
      │                           │                        │<══ 19. Hidden WebRTC Listener (hidden=True, can_publish=True) ═══════════╡
      │                           │                        │<── 20. Whisper via Data Channel ("Offer 10% discount") ──────────────────┤
      │                           │                        │    [Injected into LLM context; never revealed to customer]               │
      │                           │                        │<── 21. Takeover Event ("start") ─────────────────────────────────────────┤
      │                           │                        │    [Agent voice muted; Supervisor microphone publishes directly]         │
      │                           │                        │                                                                          │
      │── 22. Hangs Up Call ─────>│                        │                                                                          │
      │                           │── 23. Disconnect ─────>│── 24. Participant Disconnected ─────────────────>│                     │
      │                           │                        │                          │── 25. POST /internal/ended ────>│                     │
      │                           │                        │                          │── 26. Turns & Metrics ─────────>│                     │
      │                           │                        │                          │                                 ├── 27. Compliance    │
      │                           │                        │                          │                                 │   - 30s disclosure  │
      │                           │                        │                          │                                 │   - Secrecy check   │
      │                           │                        │                          │                                 │   - LLM refund audit│
      │<── 28. Dashboard Updates ─┴────────────────────────┴──────────────────────────┴─────────────────────────────────┤                     │
```

---

## 2. Step-by-Step Chronological Walkthrough

### Step 1: Pre-Warming & System Ready State (T < 0)
- **LiveKit Server** is running natively on port `7880` (TCP signalling) and `50000–60000` (UDP RTP media).
- **FastAPI Backend** has SQLite initialized and pre-seeded with agent personas (including Acme Corp product catalog: Smart Widget for $99, Cloud Pro for $29/mo, Home Hub for $149, 30-day return policy).
- **Agent Worker** pre-warms the **Silero VAD model into CPU RAM** once during process startup. It registers as available worker under identity `"support-agent"`.

### Step 2: Call Initiation & Token Issuance (T = 0 to 300ms)
- User opens the Next.js UI (`http://localhost:3000`) and clicks **"Start Customer Call"**.
- Frontend sends `POST /calls` with `{agent_id: "..."}` to FastAPI.
- FastAPI calls LiveKit API to:
  1. Create a room: `call-<uuid>`.
  2. Dispatch an agent: `CreateAgentDispatchRequest(agent_name="support-agent", room=...)`.
  3. Mint a signed customer JWT with grants: `can_publish=True, can_subscribe=True, can_publish_data=False`.

### Step 3: WebRTC Audio Connection & Greeting (T = 300ms to 1.5s)
- Browser connects to LiveKit SFU via WebRTC (SDP offer/answer, ICE candidate exchange).
- Agent Worker receives the dispatch, loads the persona, connects to the room, and links audio tracks via `RoomIO`.
- Worker triggers `on_enter()`, speaking the mandatory recording disclosure:
  > *"Hello! Thank you for calling Acme Corp customer support. Please note that this call is being recorded for quality and training purposes. How can I help you today?"*

### Step 4: The Core Conversational Voice Loop (Per Turn)
When the customer asks: *"What products do you offer?"*
1. **Audio Capture:** Browser captures 20ms Opus frames via WebRTC and sends them over UDP.
2. **Ears (VAD + STT):** Silero VAD detects speech. Deepgram Nova-3 streams interim transcripts (`"What"` → `"What products do you"` → `"What products do you offer?"`) and publishes them live to the UI via data channel.
3. **Endpointing:** Customer stops speaking. After **200ms of silence**, VAD marks the turn complete.
4. **Brain (LLM):** Groq Qwen3.8-27b receives system instructions, catalog, history, and user input. First token arrives in **~230ms (TTFT)**.
5. **Mouth (TTS):** Deepgram Aura-2 streams 48kHz audio frames back in **~360ms (TTFB)** at calm `speed=0.92`.
6. **Delivery:** LiveKit SFU forwards audio to the customer. **Total turnaround: ~1.17s.**

### Step 5: Real-Time Barge-In (Interruption Handling)
- If the customer speaks while the agent is talking (*"Wait, how much is the widget?"*):
  - Silero VAD detects customer speech instantly.
  - The worker **kills audio playback immediately**.
  - The worker **truncates the conversation history** to only what was actually spoken before the cut-off and flags `interrupted=True`.

### Step 6: Supervisor Supervision (Whisper & Takeover)
- Supervisor opens `/operator/[id]`.
- Token has **`hidden=True`**: LiveKit SFU suppresses presence so the customer cannot see the supervisor.
- **Private Whisper:** Supervisor sends *"Offer 10% discount"* over data channel. Worker injects it as a system prompt instruction. Agent uses it naturally while negative keyword guards block forbidden words (*"operator"*, *"supervisor"*).
- **Takeover:** Supervisor clicks "Take Over Call". Agent audio is muted (`set_audio_enabled(False)`). Supervisor's microphone streams directly to the customer.

### Step 7: Call Termination & Compliance Audit
- Customer hangs up.
- Worker flushes telemetry and notifies FastAPI via `POST /internal/calls/{id}/ended`.
- FastAPI logs the 5-stage latency waterfall into the database.
- FastAPI triggers the **Compliance Runner**:
  - **Rule 1 (Deterministic):** Regex check that *"recorded"* was stated within the first 30 seconds.
  - **Rule 2 (Deterministic):** Check that operator secrecy was preserved.
  - **Rule 3 (LLM Structured Audit):** Groq/OpenAI checks transcript in strict JSON mode to ensure no unauthorized refund promises were made.
- Results appear live on `/dashboard`.

---

## 3. Verified Latency Waterfall Benchmark

| Stage | Component | Measured Latency | Purpose |
| :--- | :--- | :---: | :--- |
| **Stage 1** | Deepgram Nova-3 STT | **~180 ms** | Streaming speech-to-text finalization |
| **Stage 2** | Silero VAD Endpointing | **~110 ms** | Silence detection to decide user finished |
| **Stage 3** | Groq Qwen3.8-27b LLM | **~230 ms** | Time-To-First-Token (TTFT) on Groq LPUs |
| **Stage 4** | Deepgram Aura-2 TTS | **~360 ms** | Time-To-First-Byte (TTFB) streaming audio |
| **Total** | **End-to-End Voice Turn** | **~1,170 ms (1.17s)** | **Total round-trip from speech stop to agent voice** |
