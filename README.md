# MEMORA

MEMORA is a voice-powered autonomous memory and action assistant built for the hackathon.

## Architecture & Integration Pipeline
- **Omi**: Real-time voice and ambient transcription input.
- **Qdrant**: Persistent vector memory and semantic retrieval engine.
- **Lyzr**: Agent reasoning, planning, and task orchestration.

```
[ User Voice ] ──> [ Omi Wearable / App ]
                           │ (Live Transcripts)
                           ▼
                  [ MEMORA Backend ]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [ FastEmbed Vectorizer ]      [ Lyzr Reasoning Agent ]
             │                           │
             ▼                           ▼
    [ Qdrant Vector Store ] ◄────────────┘
        (voice_memory)
```

## Milestone 1: Backend Foundation
- FastAPI backend application with health check endpoint (`/health`).
- FastEmbed semantic embedding pipeline using `BAAI/bge-small-en-v1.5` (384 dimensions).
- Qdrant integration supporting both standalone server (`localhost:6333`) and local embedded storage (`./qdrant_storage`).
- Memory storage and semantic retrieval utilities.

## Setup & Running

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
By default, MEMORA runs in local embedded mode without needing any external server. To connect to a running Qdrant instance, set `QDRANT_URL=http://localhost:6333`.

### 3. Run Backend Server
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Endpoints
- `GET /health` - Health check status.
- `POST /memories` - Store a memory entry.
- `POST /memories/search` - Retrieve semantically relevant memories.
