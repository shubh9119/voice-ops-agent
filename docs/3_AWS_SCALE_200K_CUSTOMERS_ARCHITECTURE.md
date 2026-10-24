# Architecture 3: AWS Production Deployment at Scale (200,000 Customers)

> **Document Purpose:** Production enterprise cloud deployment architecture designed to handle 200,000 registered users with peak concurrency of **10,000 to 20,000 simultaneous WebRTC phone calls** on Amazon Web Services (AWS).

---

## 1. Scale & Capacity Sizing Math

### Traffic & Concurrency Assumptions
- **Total User Base:** 200,000 customers.
- **Peak Concurrency (5%–10% simultaneous calling):** **10,000 to 20,000 concurrent calls**.
- **Audio Bandwidth per Call:** 
  - Opus audio stream = ~50 kbps per participant.
  - 10,000 concurrent calls = **500 Mbps continuous network ingress/egress**.
  - 20,000 concurrent calls = **1.0 Gbps continuous network ingress/egress**.

### Infrastructure Node Sizing
1. **LiveKit SFU Sizing:**
   - A single 16-core, 32GB RAM compute-optimized node (e.g. AWS `c6i.4xlarge`) comfortably routes **2,000 to 2,500 concurrent audio streams**.
   - For 10,000 calls: We run **6 to 8 LiveKit SFU instances** clustered across 3 Availability Zones.
2. **Voice Agent Worker Sizing:**
   - Agent workers are CPU-bound on VAD audio chunking and speech frame processing.
   - A 4-core, 8GB container worker handles **~50 concurrent calls**.
   - For 10,000 calls: We run **200 worker pods** managed dynamically by **KEDA (Kubernetes Event-driven Autoscaling)**.
3. **Database & Connection Pooling:**
   - 10,000 calls generate frequent turn updates. SQLite will fail from file locking.
   - We deploy **Amazon Aurora PostgreSQL (Multi-AZ)** fronted by **PgBouncer** connection poolers to handle 10,000+ short-lived connections.

---

## 2. AWS Production Architecture Diagram

```
                                [Global Users / Browsers]
                                            │
                                            ▼
                    [Route 53: Latency-Based Geo-DNS + Health Checks]
                                            │
                                            ▼
                           [Cloudflare Enterprise DDoS / WAF]
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
       [US-East (Primary Region: N. Virginia)]        [US-West (Failover Region: Oregon)]
  ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
  │  AWS Network Load Balancer (NLB)             │  │  AWS Network Load Balancer (NLB)             │
  │  - TCP 7880 (Signalling / REST)              │  │  - TCP 7880 (Signalling / REST)              │
  │  - TCP 7881 (ICE TCP Fallback)               │  │  - TCP 7881 (ICE TCP Fallback)               │
  │  - UDP 50000–60000 (RTP/RTCP Media)          │  │  - UDP 50000–60000 (RTP/RTCP Media)          │
  └──────────────────────┬───────────────────────┘  └──────────────────────┬───────────────────────┘
                         │                                                 │
                         ▼                                                 ▼
  ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
  │  Amazon EKS Cluster (Kubernetes 1.30)        │  │  Amazon EKS Cluster (Kubernetes 1.30)        │
  │                                              │  │                                              │
  │  ┌────────────────────────────────────────┐  │  │  ┌────────────────────────────────────────┐  │
  │  │ LiveKit SFU Cluster (6x c6i.4xlarge)   │  │  │  │ LiveKit SFU Cluster (6x c6i.4xlarge)   │  │
  │  │ - Inter-SFU mesh routing               │  │  │  │ - Inter-SFU mesh routing               │  │
  │  └───────────────────┬────────────────────┘  │  │  └───────────────────┬────────────────────┘  │
  │                      │                       │  │                      │                       │
  │  ┌───────────────────▼────────────────────┐  │  │  ┌───────────────────▼────────────────────┐  │
  │  │ Agent Worker Pool (KEDA Autoscaling)   │  │  │  │ Agent Worker Pool (KEDA Autoscaling)   │  │
  │  │ - 50 to 250 Pods (c6i.2xlarge nodes)   │  │  │  │ - 50 to 250 Pods (c6i.2xlarge nodes)   │  │
  │  │ - Silero VAD pre-warmed per Pod        │  │  │  │ - Silero VAD pre-warmed per Pod        │  │
  │  └───────────────────┬────────────────────┘  │  │  └───────────────────┬────────────────────┘  │
  │                      │                       │  │                      │                       │
  │  ┌───────────────────▼────────────────────┐  │  │  ┌───────────────────▼────────────────────┐  │
  │  │ FastAPI Backend Services (m6i.xlarge)  │  │  │  │ FastAPI Backend Services (m6i.xlarge)  │  │
  │  │ - Room dispatcher & Token minter       │  │  │  │ - Room dispatcher & Token minter       │  │
  │  │ - Background Compliance Runners        │  │  │  │ - Background Compliance Runners        │  │
  │  └───────────────────┬────────────────────┘  │  │  └───────────────────┬────────────────────┘  │
  └──────────────────────┼───────────────────────┘  └──────────────────────┼───────────────────────┘
                         │                                                 │
                         ▼                                                 ▼
  ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
  │  Amazon ElastiCache for Redis (Cluster Mode) │◄─┼─► Global Redis Cross-Region Replication      │
  │  - LiveKit Room routing & participant state  │  │  - Active-Active session distribution        │
  │  - Distributed lock manager & rate limits    │  │                                              │
  └──────────────────────┬───────────────────────┘  └──────────────────────┬───────────────────────┘
                         │                                                 │
                         ▼                                                 ▼
  ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
  │  PgBouncer Connection Pooler                 │  │  PgBouncer Connection Pooler                 │
  └──────────────────────┬───────────────────────┘  └──────────────────────┬───────────────────────┘
                         │                                                 │
                         ▼                                                 ▼
  ┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
  │  Amazon Aurora PostgreSQL (Multi-AZ)         │◄─┼─► Aurora Global Database (Read Replica)      │
  │  - Primary Writer instance in us-east-1      │  │  - <1s replication latency                   │
  │  - Auto-scaling read replicas                │  │  - Auto-failover target                      │
  └──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │  Amazon S3 (Call Recordings & Artifacts)     │
  │  - LiveKit Egress audio uploads              │
  │  - S3 Lifecycle Rule: Glacier after 30 days  │
  └──────────────────────────────────────────────┘
```

---

## 3. AWS Component Breakdown

### 1. Global Ingress & Traffic Management
- **Amazon Route 53:** Latency-based routing directs users to the nearest AWS region (e.g., `us-east-1` vs `eu-west-1`). Built-in health checks automatically fail over traffic if an entire region goes down.
- **AWS Network Load Balancer (NLB):** Layer 4 pass-through load balancer.
  - Handles millions of concurrent UDP and TCP connections with zero latency penalty.
  - Terminating TLS at the NLB using AWS ACM certificates.
  - Routes UDP traffic (`50000–60000`) directly to LiveKit SFU host nodes without NAT overhead using AWS SR-IOV enhanced networking.

### 2. LiveKit SFU Cluster on Amazon EKS
- **Deployment Model:** StatefulSet on AWS Elastic Kubernetes Service (EKS).
- **Node Type:** Compute-optimized EC2 instances (`c6i.4xlarge`, 16 vCPU, 32GB RAM).
- **Inter-Node Mesh:** When participant A connects to SFU 1 and participant B connects to SFU 2 in the same room, LiveKit SFUs route RTP packets across an internal mesh network over 10 Gbps private AWS VPC links.

### 3. Voice Agent Workers & KEDA Autoscaling
- **Node Type:** `c6i.2xlarge` EC2 worker instances.
- **Autoscaling Mechanism:** We use **KEDA (Kubernetes Event-driven Autoscaling)**.
  - Traditional CPU-based autoscaling is too slow for phone calls (spikes happen in seconds).
  - KEDA monitors the **LiveKit server's pending dispatch queue length**.
  - When pending calls spike, KEDA scales worker pods from 50 to 250 instances in **under 20 seconds**.
- **Process Pre-warming:** Every container image boots with Silero VAD pre-warmed in memory so the pod can accept calls immediately.

### 4. Distributed State & Data Tier
- **Amazon ElastiCache for Redis (Cluster Mode Enabled):**
  - LiveKit SFUs use Redis to share room-to-node routing tables, participant counts, and active worker dispatches.
  - Cross-region replication ensures session continuity.
- **Amazon Aurora Serverless v2 PostgreSQL:**
  - Auto-scales from 2 ACUs up to 64 ACUs depending on write volume.
  - Stores calls, transcripts, latency metrics, and compliance audits.
  - **PgBouncer** sits between FastAPI and PostgreSQL to pool 10,000+ short-lived connections into a reusable pool of 100 persistent database connections.

### 5. Call Archival & LiveKit Egress
- When call recording is enabled, the **LiveKit Egress service** encodes composite audio and uploads directly to an **Amazon S3** bucket.
- **S3 Lifecycle Policy:** Transition audio files to S3 Standard-Infrequent Access after 14 days, and to Amazon S3 Glacier Flexible Retrieval after 90 days for compliance archival.

### 6. Observability & Monitoring
- **Prometheus & Grafana:** Monitors SFU packet loss, jitter buffer delays, audio packet drops, and active participant counts.
- **OpenTelemetry & AWS CloudWatch:** Traces the 5-stage latency waterfall across distributed microservices.
- **Datadog / PagerDuty:** Triggers automated alarms if end-to-end voice latency exceeds 1,500ms or if compliance pass rate drops below 95%.

---

## 4. Cost Breakdown & Unit Economics at Scale

### Cost Per Call-Minute (10,000 Concurrent Calls):

| Component | AWS Resource / API Provider | Pricing Model | Cost / Call-Minute |
| :--- | :--- | :--- | :---: |
| **STT** | Deepgram Nova-3 | $0.0043 per streaming minute | **$0.0043** |
| **LLM Inference** | Groq Qwen3.8-27b | $0.59 / 1M tokens (~300 tokens/min) | **$0.0003** |
| **TTS Synthesis** | Deepgram Aura-2 | $0.015 / 1,000 characters (~400 chars/min) | **$0.0060** |
| **SFU EC2 Compute** | 8x `c6i.4xlarge` EC2 nodes | $0.68 / hr per node ($5.44/hr total) | **$0.0022** |
| **Worker EC2 Compute** | 30x `c6i.2xlarge` EC2 nodes | $0.34 / hr per node ($10.20/hr total) | **$0.0017** |
| **Data Transfer Out** | AWS VPC Egress (50 kbps stream) | $0.05 / GB transferred | **$0.0003** |
| **Database & Redis** | Aurora Serverless + ElastiCache | Fixed base + auto-scale capacity | **$0.0006** |
| **TOTAL** | — | — | **~$0.0154 / minute** |

### What this means financially:
- **A 5-minute customer support call costs ~$0.077 (under 8 cents).**
- **Monthly Bill for 1,000,000 Call-Minutes (200k customers):**
  - **Total Cost:** **~$15,400 / month**.
  - Compared to human support agents ($3,500/month per agent &rarr; 150 agents = $525,000/month), this system delivers a **97.1% cost reduction**.

---

## 5. High Availability & Disaster Recovery (DR)

1. **Multi-AZ Redundancy:** EKS worker nodes, LiveKit SFUs, and Redis nodes are balanced equally across 3 AWS Availability Zones (`us-east-1a`, `us-east-1b`, `us-east-1c`). The loss of an entire data center does not drop existing calls.
2. **Active-Passive Multi-Region Failover:** Route 53 monitors the primary region. If `us-east-1` experiences a major outage, traffic routes to `us-west-2` within 30 seconds.
3. **ICE Restart on Network Glitches:** If a customer switches from Wi-Fi to cellular data during a call, WebRTC initiates an **ICE Restart**. The media stream reconnects in under 200ms without terminating the call or losing the conversational state.
