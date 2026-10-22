# Interview Review Call Preparation Guide

This guide provides precise, expert-level explanations for the technical concepts and architectural questions covered during the 45–60 minute technical review call.

---

## 1. LiveKit Architecture & Framework

### Q: What is an SFU, and why does LiveKit forward media instead of mixing it?
- **Answer:** A Selective Forwarding Unit (SFU) receives audio and video streams from publishers and selectively routes (forwards) packets to subscribed participants without decoding, uncompressing, or re-encoding the media.
- **Why not an MCU (Multipoint Control Unit / Mixer)?**
  1. **Latency:** Mixing requires decoding Opus frames, summing audio waveforms, and re-encoding, which adds 30–80ms of processing latency. Forwarding introduces <2ms delay.
  2. **CPU & Scalability:** Encoding audio/video is extremely compute-intensive. An MCU server saturates at dozens of streams; an SFU server can easily forward thousands of streams per core.
  3. **Client Autonomy:** With an SFU, each client receives discrete audio tracks. Clients can independently mute, adjust volume, or perform client-side spatial audio.

### Q: How do Rooms, Participants, and Tracks interact?
- A **Room** is a stateful container managed by the SFU.
- A **Participant** represents an endpoint connected to the room (`LocalParticipant` vs `RemoteParticipant`).
- A participant **publishes** `Track`s (e.g. microphone audio). Other participants **subscribe** to those tracks.
- When an operator connects with `hidden=true` in their `VideoGrants`, the SFU suppresses `participant_joined` notifications for other clients, keeping them completely invisible to the customer.

### Q: How does the Agent Worker dispatch model work?
1. **Worker Registration:** When `python -m voiceagent.main` starts, it connects via WebSocket to `ws://livekit:7880/agent` and registers under `agent_name="support-agent"`.
2. **Dispatch Creation:** The backend API creates an explicit dispatch request (`CreateAgentDispatchRequest`) specifying `agent_name="support-agent"`, the target `room="call-<id>"`, and `metadata={"call_id": "...", "agent_id": "..."}`.
3. **Job Assignment:** The LiveKit SFU matches the dispatch to an available, least-loaded registered worker process and sends a `JobContext`.
4. **Room Join:** The worker accepts the job, uses its internal admin token to join `call-<id>`, reads the metadata, fetches the prompt from FastAPI, and starts the voice pipeline.

### Q: How does AgentSession handle VAD, Turn Detection, and Barge-in?
- **VAD (Silero):** Runs continuously on raw PCM audio frames (16kHz). Detects whether human speech is occurring.
- **Turn Detection:** A semantic multilingual model evaluates the ongoing STT transcript against language patterns to determine if the speaker has finished their sentence or is just pausing (e.g. "I want to ask..." vs "I want to ask about my bill.").
- **Interruption (Barge-in):** If Silero VAD fires while the agent is playing audio through the TTS track, the session immediately cancels TTS streaming and sends a silence frame. Crucially, `ChatMessage.content` is truncated to only what was actually forwarded before interruption, preserving conversation context integrity.

### Q: Reliable vs. Lossy Data Channels — When to use which?
- **Reliable Data Channel (SCTP retransmissions, ordered):** Used for **Whispers**, **Takeover signals**, and **Final Transcripts**. A missing whisper or takeover command could break supervisor guidance, so guaranteed delivery is essential.
- **Lossy Data Channel (SCTP unordered, zero retries):** Used for high-frequency telemetry, interim transcript updates, and live audio volume levels. If a volume level packet is dropped, subsequent packets render it obsolete anyway.

### Q: Egress, Ingress, and SIP at a high level
- **Egress:** LiveKit's recording service. Spawns headless Chromium or GStreamer workers in Docker/Kubernetes to capture room composite audio/video or individual tracks and upload MP4/OGG files to Amazon S3 / Google Cloud Storage.
- **Ingress:** Ingests external RTMP, WHIP, or SRT streams into a LiveKit room.
- **SIP (Session Initiation Protocol):** LiveKit SIP gateway connects to PSTN carriers (Twilio, Telnyx). Translates G.711 telephony audio over RTP to Opus over WebRTC, allowing agents to answer traditional phone calls.

### Q: Self-Hosted vs. LiveKit Cloud
- **Self-Hosted:** Full data privacy (audio never leaves your VPC/servers), no per-minute SFU SaaS fees, complete control over network topology and UDP port ranges. Requires operating TURN servers, SSL termination, and horizontal autoscaling via Redis.
- **LiveKit Cloud:** Managed global mesh of SFUs with automated geo-DNS routing and built-in TURN relays, but charges per participant-minute.

---

## 2. WebRTC Deep Dive

### Q: Explain the WebRTC Connection Lifecycle
1. **Signalling:** Out-of-band exchange (WebSocket on port 7880) of SDP offers and answers.
2. **SDP (Session Description Protocol):** Declares media capabilities, codecs (Opus 48kHz, mono/stereo), encryption fingerprints (DTLS), and network transport parameters.
3. **ICE (Interactive Connectivity Establishment):** Discovers IP pathways between peers. Candidates gathered:
   - `host`: Local private IP addresses on the machine network adapter.
   - `srflx` (Server Reflexive): Public IP and mapped port discovered via STUN.
   - `relay`: Relayed IP address via TURN server.
4. **DTLS Handshake:** Diffie-Hellman key exchange over the chosen candidate pair to derive SRTP encryption keys.
5. **Media Flow:** SRTP audio packets stream over UDP.

### Q: STUN vs TURN — When is TURN needed, and what does it cost?
- **STUN (Session Traversal Utilities for NAT):** Lightweight protocol. Asks the server *"What is my public IP and port as seen by the internet?"* Fails when both peers are behind Symmetric NATs (where the NAT creates a different port mapping for each destination).
- **TURN (Traversal Using Relays around NAT):** Media relay server. When peer-to-peer or direct SFU connection fails, all audio packets are relayed through the TURN server.
- **Cost:** High bandwidth consumption. Relaying 10,000 calls at 50 kbps requires ~500 Mbps sustained server egress bandwidth.

### Q: Why UDP instead of TCP? What do Jitter Buffers and Packet Loss Concealment do?
- **Why UDP:** Real-time speech cannot wait for TCP acknowledgments and retransmissions. If packet #4 arrives 150ms late because packet #3 was retransmitted, packet #4 is already obsolete in a live conversation.
- **Jitter Buffer:** Smooths out packet arrival variations. Holds a tiny buffer (20–40ms) of audio packets so they can be played back continuously without stuttering.
- **Opus PLC (Packet Loss Concealment):** When a packet is lost, the Opus decoder synthesizes plausible audio based on the pitch and spectrum of previous frames, making packet loss up to 10% nearly imperceptible.

### Q: Opus vs G.711 Telephony
- **G.711 (Traditional PSTN):** Fixed 64 kbps, narrow-band (8 kHz sample rate, 300–3400 Hz frequency response). Audio sounds muffled ("telephone sound") and has no native packet loss concealment.
- **Opus (WebRTC):** Dynamic bitrate (6 kbps to 510 kbps), full-band (48 kHz sample rate, 20 Hz to 20,000 Hz). Delivers studio-quality conversational speech with dynamic bitrate adaptation to network congestion.

---

## 3. Production Scaling & Latency Engineering

### Q: How would you scale this to 10,000 concurrent calls?
1. **Bottleneck Analysis (What runs out first?):**
   - **1st Bottleneck: External Provider Rate Limits.** Groq, Deepgram, and OpenAI have strict requests-per-minute (RPM) and tokens-per-minute (TPM) quotas. At 10,000 calls, you need enterprise dedicated endpoints or self-hosted vLLM clusters.
   - **2nd Bottleneck: Agent Worker CPU.** Silero VAD, turn detection, and WebSocket streaming consume ~0.05–0.1 CPU cores per concurrent call. 10,000 calls require ~500–1000 CPU cores across worker pools.
   - **3rd Bottleneck: SFU Network Egress.** Each audio stream is ~40 kbps. 10,000 calls = ~800 Mbps aggregate throughput. A cluster of 4–6 LiveKit SFU instances with a Redis state store easily handles this.
2. **Architecture:**
   - Multi-node LiveKit SFU cluster with Redis room routing.
   - Kubernetes Horizontal Pod Autoscaler (HPA) for Python agent workers based on CPU and session count.
   - Region-specific deployments (US-East, US-West, EU-Central) to minimize speed-of-light network latency to users.

### Q: What is the cost per call-minute, and where does it go?
- **Deepgram STT (Streaming Nova-3):** ~$0.0043 / min
- **Groq LLM (LLaMA 3.3 70B, ~300 tokens/min):** ~$0.0030 / min
- **Deepgram TTS (Aura-2, ~800 characters/min):** ~$0.0120 / min
- **LiveKit Self-Hosted Compute & Bandwidth:** ~$0.0015 / min
- **Total:** **~$0.021 per call-minute** (~$1.25 / hour).
- **Where most of it goes:** TTS (text-to-speech) audio synthesis accounts for over 55% of total operating cost.

### Q: Failure Handling & Resilience
- **Worker Crash Mid-Call:** The customer remains in the LiveKit room. LiveKit detects worker disconnect via heartbeat timeout and can re-dispatch the job. The FastAPI backend logs the disconnect, and the replacement worker reloads the conversation history from the DB.
- **SFU Node Crash:** WebRTC connection drops. The client's `livekit-client` automatically initiates an ICE restart and reconnects to a healthy SFU node in the cluster.

### Q: Where does latency come from, and which stage would you attack first?
- **Latency Breakdown (p50):**
  - VAD / Turn Decision: ~120ms
  - STT Final Transcript: ~180ms
  - LLM First Token (Groq): ~95ms
  - TTS First Audio Byte: ~140ms
  - Network & Playback Buffer: ~45ms
  - **Total E2E:** **~580ms**
- **First Attack Vector:** **End-of-Turn Decision.** Traditional VAD waits for 500ms of silence before declaring the turn complete. By tuning `min_endpointing_delay` to 0.25s and combining it with semantic turn prediction (LiveKit multilingual model), you save 150–200ms without false interruptions.
- **Second Attack Vector:** **Speculative / Preemptive LLM Generation.** Send interim transcripts to the LLM when confidence reaches 85%. If the user completes the expected phrase, the LLM has already generated the first tokens, cutting perceived TTFT to near zero.
