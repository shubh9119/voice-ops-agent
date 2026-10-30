# Omnibound — Brand Q&A Agent

An enterprise-ready, multi-tenant RAG (Retrieval-Augmented Generation) system built with **FastAPI**, **LangGraph**, **ChromaDB**, **Google Gemini**, and a **Next.js** dashboard.

Designed specifically for marketing and brand intelligence teams to monitor and query how their products appear in web content, review platforms, and comparison articles — with strict tenant isolation and honest hallucination prevention.

---

## 🏗️ Architecture Overview

```
                      ┌───────────────────────────────────────────┐
                      │            Next.js Dashboard              │
                      │   (Tenant Context, Ingest & Q&A Chat)     │
                      └─────────────────────┬─────────────────────┘
                                            │ REST API
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │             FastAPI Backend               │
                      │  /health  |  /ingest  |  /ask             │
                      └─────────────┬───────────────┬─────────────┘
                                    │               │
                     Ingestion Flow │               │ Query Flow
                                    ▼               ▼
                      ┌──────────────────┐  ┌─────────────────────┐
                      │ Ingestion Engine │  │   LangGraph Agent   │
                      │  • URL/Text fetch│  │   • retrieve        │
                      │  • SHA256 doc_id │  │   • grade (LLM)     │
                      │  • RecursiveSplit│  │   • decision (retry)│
                      │  • 400ch / 50ovlp│  │   • answer (LLM)    │
                      └─────────────┬────┘  └───────────────┬─────┘
                                    │                       │
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │       ChromaDB        │
                                    │  Isolated Collections │
                                    │  `omnibound_{tenant}` │
                                    └───────────────────────┘
```

---

## 🚀 Key Features

1. **Strict Multi-Tenant Isolation**:
   - Every tenant is strictly isolated by dedicated vector store collections (`omnibound_{tenant_id}`).
   - Data ingested for tenant `acme` is never leaked or visible to tenant `globex`.
2. **Idempotent Ingestion Pipeline**:
   - Computes a deterministic SHA-256 hash of document content/URL as `doc_id`.
   - Chunks are keyed as `{doc_id}-{chunk_index}` and upserted.
   - Re-ingesting the exact same document multiple times never inflates chunk counts.
3. **LangGraph StateGraph Agent**:
   - **`retrieve`**: Queries top-5 chunks using semantic embeddings within the tenant namespace.
   - **`grade`**: Evaluates each retrieved chunk using an LLM relevance filter (`yes` / `no`).
   - **`decision` (conditional edge)**:
     - If relevant chunks exist $\to$ proceeds to `answer`.
     - If no relevant chunks and `retry_count == 0` $\to$ invokes `rewrite` to optimize search query and retries retrieval.
     - If no relevant chunks after retry $\to$ terminates with `found_in_corpus = false`.
   - **`answer`**: Generates a concise synthesis strictly grounded in relevant chunks, returning full citations and execution trace.
4. **Honest "Not Found" Behavior**:
   - Out-of-corpus queries (e.g., *"What is the capital of France?"*) are never hallucinated. The agent explicitly reports that the answer is not in the corpus.
5. **Modern Next.js Interface**:
   - Switch active tenant with 1 click.
   - Live backend health indicator (`GET /health`).
   - One-click button to seed a complete 10-article project management corpus.
   - Visual execution trace timeline and collapsible source citation cards.

---

## 🛠️ Tech Stack & Trade-offs

| Component | Choice | Trade-off / Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | Async-native performance, native Pydantic schema validation, automatic OpenAPI / Swagger interactive documentation. |
| **Agent Workflow** | **LangGraph** | Enables cyclic graphs and dynamic conditional branches required for iterative search query rewriting and grading, unlike linear chains. |
| **Vector Database** | **ChromaDB** | Zero external infrastructure required; lightweight and persistent. Supports collection-based tenant isolation. *Trade-off: In hyper-scale multi-node production, a managed distributed store like Pinecone or pgvector with row-level security would replace embedded ChromaDB.* |
| **LLM & Embeddings** | **Google Gemini 2.0 Flash + text-embedding-004** | Fast latency, generous free-tier quotas (1,500 RPM for embeddings, 15 RPM / 1M tokens/day for LLM), reliable instruction following. |
| **Frontend** | **Next.js 14 (App Router) + Tailwind CSS** | Fast, responsive UI with server-rendered layout and responsive client-side interactivity. |

---

## ⚡ Quick Start

### Option 1: Docker Compose (One-command run)

```bash
# 1. Clone repository and navigate to folder
cd HomeAssigmnentNeuro

# 2. Configure environment
cp backend/.env.example backend/.env
# Add your GOOGLE_API_KEY into backend/.env

# 3. Start everything with Docker
docker compose up --build
```
- Frontend UI: [http://localhost:3000](http://localhost:3000)
- Backend API & Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### Option 2: Local Development

```bash
# Windows
start.bat

# Linux / macOS
chmod +x start.sh
./start.sh
```

---

## 🧪 Automated Tests (Mocked LLM, Zero API Key Required)

The test suite validates the core business rules using mocked LLM and deterministic embedding fixtures:
1. **Tenant Isolation**: Verifies that tenant `globex` receives no data when querying information ingested exclusively by `acme`.
2. **Idempotent Ingestion**: Verifies vector counts do not duplicate upon repeated ingestion of the same document.
3. **Decision Logic**: Validates the 3 LangGraph paths:
   - Relevant chunks $\to$ answer generated with citations.
   - Irrelevant chunks $\to$ query rewritten $\to$ retry $\to$ not found.
   - Empty tenant $\to$ immediate honest refusal.

Run tests:
```bash
cd backend
python -m pytest tests/ -v
```

---

## 🎥 Video Walkthrough Script (10–12 Minutes)

Use this structured guide when recording your walkthrough:

1. **Start the Service (1 min)**:
   - Run `docker compose up` or `start.bat`.
   - Open browser to `http://localhost:8000/health` $\to$ show `status: "ok"`, `vector_db: "reachable"`, `llm_provider: "reachable"`.
2. **Ingest & Idempotence (2 mins)**:
   - Open `http://localhost:3000`.
   - Show tenant set to `acme`.
   - Click **"Ingest Sample Corpus (10)"** $\to$ observe response `10 docs stored, 30+ chunks stored`.
   - Click it a second time $\to$ explain that vector count did not duplicate due to SHA-256 chunk keys.
3. **Normal Question (2 mins)**:
   - Ask: *"What do reviewers say about Asana's pricing compared to Trello?"*
   - Show the generated answer, source citations, and the 3-step LangGraph trace (`retrieve` $\to$ `grade` $\to$ `answer`).
4. **Off-Topic Question (2 mins)**:
   - Ask: *"What is the capital of France?"*
   - Show that `found_in_corpus` is `false`, no answer is hallucinated, and the trace displays the rewrite retry loop:
     `retrieve` $\to$ `grade (0 relevant)` $\to$ `rewrite` $\to$ `retrieve` $\to$ `grade` $\to$ `not_found`.
5. **Tenant Isolation (1.5 mins)**:
   - Switch active tenant to `globex` using the preset button.
   - Ask the same Asana pricing question.
   - Show that `globex` gets `found_in_corpus: false` and no data is leaked from `acme`.
6. **Code Walkthrough (2.5 mins)**:
   - Show `backend/app/config.py` & `.env.example` (no hardcoded keys).
   - Ingestion: `backend/app/services/ingestion.py` (chunk size 400/50 rationale, SHA-256 doc_id).
   - LangGraph Agent: `backend/app/agents/qa_agent.py` (StateGraph, 3 nodes, conditional edge).
   - Multi-tenancy: `backend/app/services/vectorstore.py` (`omnibound_{tenant_id}` collections).
7. **Run Pytest (1 min)**:
   - Run `python -m pytest tests/ -v` showing all tests passing with mocked LLM.
8. **Reflection & Honest Trade-offs (1 min)**:
   - *Trade-off*: Local ChromaDB vs managed Pinecone.
   - *Limitation / Rough Edge*: URL scraping relies on standard HTML tags; JavaScript-heavy SPAs require headless browser rendering (e.g. Playwright).
   - *Next steps*: Hybrid keyword + semantic retrieval (BM25 + embeddings) and re-ranking with Cohere Rerank.
