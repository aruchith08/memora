# MEMORA — Voice-Powered Autonomous Memory Assistant

> **Continuous Ambient Intelligence · Semantic Vector Recall · Multi-Agent Sequential Reasoning**

[![Live Frontend](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen)](https://memora-arh.vercel.app/app)
[![Live Backend](https://img.shields.io/badge/Backend-FastAPI%20on%20Vercel-blue)](https://memora-1iae.vercel.app/health)
[![Qdrant Cloud](https://img.shields.io/badge/Vector%20DB-Qdrant%20Cloud-red)](https://qdrant.tech)
[![Lyzr Agent Studio](https://img.shields.io/badge/Orchestrator-Lyzr%20Agent%20Studio-orange)](https://studio.lyzr.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 1. Project Overview

**MEMORA** is a voice-first autonomous memory assistant that bridges ambient physical audio with semantic knowledge synthesis and multi-agent plan execution. Operating silently in the background, MEMORA listens to real-world conversations and audio streams via the **Omi** wearable app, vectorizes knowledge with **FastEmbed** into **Qdrant Cloud**, and activates a sequential multi-agent reasoning chain powered by **Lyzr** to synthesize grounded answers and actionable checklists.

### The Problem
Human memory degrades rapidly under information overload. Important action items, meeting agreements, commitments, and class instructions spoken aloud are routinely lost because taking manual notes creates cognitive friction. Existing voice assistants are reactive, lack persistent semantic context, and struggle to execute structured multi-step plans across days of conversations.

### The Solution
MEMORA creates an autonomous, privacy-conscious memory loop:
1. **Passive Transcription**: Ingests transcripts seamlessly via Omi webhooks.
2. **Semantic Vector Indexing**: Projects speech into 384-dimensional dense vectors with cosine similarity in Qdrant Cloud.
3. **Sequential Multi-Agent Deliberation**: Combines memory retrieval with a two-stage Lyzr reasoning pipeline (MEMORA Reasoner & MEMORA Action Planner).
4. **Permanent Granular Control**: Implements user-scoped memory deletion and forgetting to ensure users retain sovereign control over their knowledge base.

---

## 2. Official Hackathon Track

- **Hackathon**: *The Dawn of the Autonomous AI Builder — Stop Prompting, Solo Agents Hackathon 2026*
- **Organizers**: AI House × HiDevs
- **Selected Build Track**: **Collaborative Multi-Agent Workflows**
  *(Voice-triggered pipelines where specialized agents coordinate through a shared vector memory layer)*
- **Secondary Alignment**: **Privacy-First Knowledge Systems** *(Granular user isolation, fail-closed admin controls, and verified record deletion)*

---

## 3. Live Deployments & Repository

| Component | Target / Environment | URL |
| :--- | :--- | :--- |
| **Frontend Dashboard** | Vercel (React + Vite + Tailwind CSS) | [https://memora-arh.vercel.app/app](https://memora-arh.vercel.app/app) |
| **Public Landing Page** | Vercel SPA | [https://memora-arh.vercel.app](https://memora-arh.vercel.app) |
| **Backend Web Service** | Vercel Serverless Functions (Python ASGI) | [https://memora-1iae.vercel.app](https://memora-1iae.vercel.app) |
| **Backend Health Check** | FastAPI `/health` | [https://memora-1iae.vercel.app/health](https://memora-1iae.vercel.app/health) |
| **Source Code** | Public GitHub Repository | [https://github.com/aruchith08/memora](https://github.com/aruchith08/memora) |
| **Demo Video** | Video Walkthrough (Under 5 mins) | *[MEMORA Demo Video Link Placeholder]* |

---

## 4. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph AudioIngestion["1. Ambient Audio & Transcripts"]
        User["User Speaks in Real World"] --> OmiDevice["Omi Wearable / Mobile App"]
        OmiDevice -->|"Webhook POST /omi/conversation\n(with secret auth)"| FastAPIServer["MEMORA Backend (FastAPI on Vercel)"]
        OmiDevice -->|"Webhook POST /omi/realtime\n(streaming chunks)"| FastAPIServer
    end

    subgraph MemoryLayer["2. Dense Vector Indexing & Memory Layer"]
        FastAPIServer -->|"Text Vectorization"| FastEmbed["FastEmbed BAAI/bge-small-en-v1.5\n(384-dim dense vectors)"]
        FastEmbed -->|"Upsert with UID & Timestamp metadata"| QdrantCloud[("Qdrant Cloud Cluster\nCollection: voice_memory\nMetric: Cosine Distance")]
    end

    subgraph RetrievalAndReasoning["3. Semantic Retrieval & Multi-Agent Chain"]
        Query["User Query / Voice Prompt"] --> FastAPIServer
        FastAPIServer -->|"HNSW ANN Search (Filtered by UID)"| QdrantCloud
        QdrantCloud -->|"Top-k Relevant Contexts"| Orchestrator["MEMORA Sequential Orchestrator"]
        
        subgraph LyzrPipeline["Lyzr Multi-Agent Reasoning Chain"]
            Orchestrator -->|"Grounding + Question"| Reasoner["Agent 1: MEMORA Reasoner\n(Factual Recall & Context Extraction)"]
            Reasoner -->|"Factual Synthesis"| ActionPlanner["Agent 2: MEMORA Action Planner\n(Checklist & Next-Step Generation)"]
            ActionPlanner -->|"Synthesized Plan"| FinalOutput["Unified Response & Audit Trail"]
        end
    end

    subgraph PresentationAndFeedback["4. User Dashboard & Outbound Delivery"]
        FinalOutput -->|"Persisted Audit Record"| LocalAudit["/tmp/latest_reasoning_result.json\nGET /reason/latest"]
        FinalOutput -.->|"Optional Outbound Alert"| OmiNotification["Omi App Notification API"]
        LocalAudit --> Dashboard["React Dashboard\n• System Health\n• Semantic Search\n• Multi-Agent Trace\n• Memory Timeline\n• Forget / Delete Controls"]
    end
```

---

## 5. Technology Stack & Component Roles

### **Omi (Ambient Voice & Conversation Ingestion)**
Omi serves as the voice interface. Transcripts from live physical conversations and streaming chunks are ingested through authenticated webhook endpoints (`POST /omi/conversation`, `POST /omi/realtime`). The backend enforces query-param and header-based secret verification (`OMI_WEBHOOK_SECRET`) to ensure payloads originate exclusively from trusted hardware. Inbound events are deduplicated with an in-memory lock to guarantee idempotent processing. Outbound notification capabilities are integrated to relay synthesized plans back to the wearable screen.

### **Qdrant (Vector Database & Sovereign Memory Layer)**
Qdrant Cloud provides persistent, low-latency approximate nearest neighbor (ANN) vector search. Every conversation snippet is embedded into a 384-dimensional vector using `BAAI/bge-small-en-v1.5` and stored with metadata (`uid`, `source`, `category`, `timestamp`). 
- **Identity Isolation**: A dedicated payload index on the `uid` field enforces server-side scoping so that queries strictly retrieve the active user's records.
- **Privacy & Forgetting**: Supports granular deletion (`DELETE /memories/{id}`) which permanently removes points from the vector space.

### **Lyzr (Multi-Agent Orchestration & Reasoning Chain)**
Lyzr powers the autonomous intelligence engine. Rather than relying on simple single-turn prompts, MEMORA coordinates specialized agents via the Lyzr Agent Studio API:
1. **MEMORA Reasoner** (`6ac7c057b300b2daefd99218`): Focuses strictly on factual grounding, extracting verifiable truths from retrieved Qdrant memories while eliminating hallucination.
2. **MEMORA Action Planner** (`6ac7eba918b1643ee32dad1d`): Takes the Reasoner's output and transforms it into prioritized action checklists and schedules.
3. **Lyzr Manager Agent** (`6ac7ec8f6f28ab116dc67d3b`): Handles single-focus queries and provides fallback orchestration with WebSocket telemetry monitoring.

### **Frontend & Backend Stacks**
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide icons. Client-side SPA routing managed via `vercel.json`.
- **Backend**: FastAPI (Python 3.12/3.11), Uvicorn, FastEmbed, Qdrant Client, Pydantic v2.

---

## 6. Complete API Reference

All routes are implemented and validated:

| Method | Endpoint | Description | Auth / Security |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Operational health, vector mode, and collection name | Public |
| `GET` | `/memories` | Recent memories in chronological descending order | Scoped by `DEMO_UID` |
| `POST` | `/memories` | Vectorize and insert a new text memory | `MEMORA_ADMIN_KEY` in production |
| `POST` | `/memories/search` | Semantic vector search with cosine similarity ranking | Scoped by `DEMO_UID` |
| `DELETE` | `/memories/{memory_id}` | Permanently delete/forget a specific memory | Owner verification + `MEMORA_ADMIN_KEY` |
| `POST` | `/reason` | Direct multi-agent reasoning execution | `MEMORA_ADMIN_KEY` in production |
| `GET` | `/reason/latest` | Audit trace of the latest multi-agent reasoning run | Public (sanitized, zero secrets) |
| `POST` | `/omi/conversation` | Ingest completed conversation transcript from Omi | `OMI_WEBHOOK_SECRET` |
| `POST` | `/omi/realtime` | Ingest streaming real-time transcript chunks | `OMI_WEBHOOK_SECRET` |
| `GET` | `/omi/events/{conv_id}` | Check webhook deduplication status | Public |

---

## 7. Security, Privacy & Memory Deletion

- **Zero Secret Exposure**: All credentials (`QDRANT_API_KEY`, `LYZR_API_KEY`, `OMI_WEBHOOK_SECRET`, `MEMORA_ADMIN_KEY`) are managed via environment variables and excluded from version control.
- **Fail-Closed Administrative Gate**: Mutations (`POST /memories`, `DELETE /memories/{id}`, `POST /reason`) fail closed with `401 Unauthorized` in production if `MEMORA_ADMIN_KEY` is not provided.
- **Strict Cross-User Isolation**: Vector searches and deletion requests verify that point records match the caller's authorized `uid`. Attempting to delete another user's memory returns `403 Forbidden`.
- **Permanent Forgetting**: Unlike applications that simply hide records on the frontend, `DELETE /memories/{id}` triggers `client.delete()` in Qdrant Cloud, permanently wiping the vector and payload from the cluster.
- **Serverless Writable Storage**: FastEmbed model caches and observable audit logs are isolated to `/tmp/fastembed_cache` and `/tmp/latest_reasoning_result.json`, ensuring complete compatibility with Vercel's read-only root filesystem.

---

## 8. Local Setup & Verification

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- [uv](https://docs.astral.sh/uv/) (recommended for fast Python environments)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/aruchith08/memora.git
cd memora

# Configure Backend Environment
cp backend/.env.example backend/.env
# Populate QDRANT_URL, QDRANT_API_KEY, LYZR_API_KEY, etc.
```

### 2. Run Backend
```bash
cd backend
uv run uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Run Frontend
```bash
cd ../frontend
npm install
npm run dev
# Dashboard opens at http://localhost:5173/app
```

---

## 9. Test Results & Verification

All automated test suites pass cleanly:

```bash
# 1. Run Unified Deployment & Security Test Suite (23 Tests)
uv run --directory backend -m unittest test_unified_deployment.py
# Result: Ran 23 tests in 2.68s — OK

# 2. Run Multi-Agent Orchestration & Lyzr Telemetry Suite (29 Tests)
uv run --directory backend -m unittest test_collaborative_workflow.py test_lyzr_service.py test_lyzr_telemetry.py
# Result: Ran 29 tests in 9.74s — OK

# 3. Run Frontend Typecheck & Production Build
npm --prefix frontend run build
# Result: 1,620 modules transformed into dist/ — 0 type errors
```

---

## 10. Demo Video Plan (3–4 Minutes)

- **Video Filename**: `MEMORA_Hackathon_Demo.mp4`
- **Recommended Length**: 3 minutes 30 seconds
- **Structure**:
  1. **0:00–0:25**: Introduction to MEMORA, the problem of memory decay, and the solution.
  2. **0:25–1:00**: Architecture walkthrough (Omi voice capture → Qdrant vector memory → Lyzr collaborative agents).
  3. **1:00–1:40**: Live Dashboard overview ([memora-arh.vercel.app/app](https://memora-arh.vercel.app/app)) showing connected backend and the 5 indexed demo memories.
  4. **1:40–2:20**: Live semantic search demonstration querying *"What should I prepare for my MSF class?"* (MSF class memory ranks #1 with ~78% relevance).
  5. **2:20–3:00**: Memory deletion & privacy control demo (forgetting a memory with permanent Qdrant removal).
  6. **3:00–3:30**: Conclusion, live URLs, and GitHub repository.

---

## 11. Submission Metadata

- **Project Name**: MEMORA
- **Project Title**: MEMORA — Voice-Powered Autonomous Memory Assistant
- **Track**: Collaborative Multi-Agent Workflows
- **Live Frontend**: https://memora-arh.vercel.app/app
- **Live Backend**: https://memora-1iae.vercel.app
- **Repository**: https://github.com/aruchith08/memora
- **Solo Participant Entry**: Developed for the Stop Prompting, Solo Agents Hackathon 2026.
