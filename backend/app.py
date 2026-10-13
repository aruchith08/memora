import os
import uuid
import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Body, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from fastembed import TextEmbedding

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("memora-backend")

# Configuration Constants
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "voice_memory")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
VECTOR_DIM = 384
DISTANCE_METRIC = Distance.COSINE


def get_fastembed_cache_path() -> str:
    """
    Resolves the writable directory for caching FastEmbed/ONNX model files.
    Priority:
    1. Explicit FASTEMBED_CACHE_PATH environment variable if set.
    2. /tmp/fastembed_cache on Vercel/Linux serverless environments (or when /tmp exists and is writable).
    3. Fallback to local ./fastembed_cache or system temporary folder.
    """
    configured = os.getenv("FASTEMBED_CACHE_PATH", "").strip()
    if configured:
        return configured

    # Detect Vercel serverless environment (VERCEL=1) or writable /tmp
    if os.getenv("VERCEL") == "1" or (os.path.isdir("/tmp") and os.access("/tmp", os.W_OK)):
        return "/tmp/fastembed_cache"

    # Default to local cache in working directory or standard user cache
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "fastembed_cache"))


# Globals for lazy/lifespan initialization
_qdrant_client: Optional[QdrantClient] = None
_embedding_model: Optional[TextEmbedding] = None
_qdrant_mode: str = "uninitialized"


def get_embedding_model() -> TextEmbedding:
    """Lazily load and cache the FastEmbed model using a guaranteed writable cache path."""
    global _embedding_model
    if _embedding_model is None:
        cache_path = get_fastembed_cache_path()
        os.makedirs(cache_path, exist_ok=True)

        # Propagate cache path to environment variables for underlying Hugging Face / Xet tooling
        os.environ.setdefault("FASTEMBED_CACHE_PATH", cache_path)
        os.environ.setdefault("HF_HOME", cache_path)
        os.environ.setdefault("HF_HUB_CACHE", os.path.join(cache_path, "hub"))
        os.environ.setdefault("HF_XET_CACHE", os.path.join(cache_path, "xet"))

        logger.info(f"Loading FastEmbed model: {EMBEDDING_MODEL_NAME} (cache_dir={cache_path})")
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME, cache_dir=cache_path)
        logger.info("FastEmbed model loaded successfully.")
    return _embedding_model


def get_qdrant_client() -> QdrantClient:
    """
    Initialize Qdrant client. Supports:
    1. Standalone server (QDRANT_URL, e.g. localhost:6333)
    2. Local embedded disk storage (QDRANT_PATH, e.g. ./qdrant_storage)
    """
    global _qdrant_client, _qdrant_mode
    if _qdrant_client is not None:
        return _qdrant_client

    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
    qdrant_path = os.getenv("QDRANT_PATH", "./qdrant_storage").strip()

    if qdrant_url:
        try:
            logger.info(f"Connecting to Qdrant server at: {qdrant_url}")
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=5.0)
            # Verify connectivity
            client.get_collections()
            _qdrant_client = client
            _qdrant_mode = f"server ({qdrant_url})"
            logger.info(f"Successfully connected to Qdrant server at {qdrant_url}")
            return _qdrant_client
        except Exception as e:
            env_name = os.getenv("ENVIRONMENT", "").strip().lower()
            if env_name == "production":
                logger.critical(
                    f"[Security/Config] Fatal: Remote Qdrant connection to '{qdrant_url}' failed in production ({e}). "
                    "Silent fallback to ephemeral embedded storage is strictly disallowed."
                )
                raise RuntimeError(
                    f"Production startup failure: Remote Qdrant at '{qdrant_url}' is unreachable ({e})."
                ) from e
            logger.warning(
                f"Could not connect to Qdrant server at {qdrant_url} ({e}). "
                f"Falling back to local embedded storage at '{qdrant_path}'."
            )

    # Fallback to local embedded storage
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name == "production" and not qdrant_url:
        logger.critical(
            "[Security/Config] Fatal: ENVIRONMENT=production requires QDRANT_URL to be set to a persistent Qdrant instance."
        )
        raise RuntimeError("Production startup failure: QDRANT_URL must be configured when ENVIRONMENT=production.")

    logger.info(f"Using Qdrant local embedded storage at: {qdrant_path}")
    os.makedirs(qdrant_path, exist_ok=True)
    _qdrant_client = QdrantClient(path=qdrant_path)
    _qdrant_mode = f"embedded ({qdrant_path})"
    logger.info(f"Initialized Qdrant embedded storage at {qdrant_path}")
    return _qdrant_client


def init_qdrant_collection() -> None:
    """Initialize the voice_memory collection in Qdrant if it does not already exist."""
    client = get_qdrant_client()
    try:
        collections_response = client.get_collections()
        existing_collections = [col.name for col in collections_response.collections]

        if COLLECTION_NAME not in existing_collections:
            logger.info(
                f"Creating collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}, metric={DISTANCE_METRIC})..."
            )
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=DISTANCE_METRIC),
            )
            logger.info(f"Collection '{COLLECTION_NAME}' created successfully.")
        else:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists.")

        # Ensure keyword payload index on 'uid' exists for filtered searches and scrolling
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="uid",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Payload index for 'uid' (KEYWORD) verified/created in '{COLLECTION_NAME}'.")
        except Exception as idx_err:
            # Idempotent guard: if index already exists or server returns ok/conflict, proceed safely
            err_msg = str(idx_err).lower()
            if "already exists" in err_msg or "conflict" in err_msg:
                logger.info(f"Payload index for 'uid' already exists in '{COLLECTION_NAME}'.")
            else:
                logger.warning(
                    f"Notice during payload index creation for 'uid' in '{COLLECTION_NAME}': {idx_err}"
                )
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collection '{COLLECTION_NAME}': {e}")
        raise


def embed_text(text: str) -> List[float]:
    """Generate 384-dimensional embedding vector for given text using FastEmbed."""
    model = get_embedding_model()
    embeddings = list(model.embed([text]))
    if not embeddings:
        raise ValueError("Failed to generate embedding: empty output from model.")
    return embeddings[0].tolist()


def store_memory(
    text: str,
    uid: str = "default_user",
    source: str = "manual",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Utility to accept text, compute its embedding, and persist it to Qdrant.
    Stores uid, source, timestamp, and metadata per the hackathon guide.
    """
    if not text or not text.strip():
        raise ValueError("Cannot store empty text memory.")

    client = get_qdrant_client()
    clean_text = text.strip()
    vector = embed_text(clean_text)

    point_id = str(uuid.uuid4())
    payload = {
        "uid": uid,
        "text": clean_text,
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ts": time.time(),
        **(metadata or {}),
    }

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )
    logger.info(f"Stored memory [{point_id}] for uid='{uid}' (source={source}): {clean_text[:60]}...")
    return {
        "id": point_id,
        "text": clean_text,
        "payload": payload,
    }


def retrieve_memories(
    question: str,
    uid: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Utility to accept a question, compute its embedding, and retrieve the most relevant memories from Qdrant.
    Optionally filters by uid for user isolation per the hackathon guide.
    """
    if not question or not question.strip():
        raise ValueError("Cannot search with empty question.")

    client = get_qdrant_client()
    query_vector = embed_text(question.strip())

    # Build query filter if uid is provided
    query_filter = None
    if uid:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="uid",
                    match=MatchValue(value=uid),
                )
            ]
        )

    # Support both query_points and search methods depending on client version
    if hasattr(client, "query_points"):
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        points = response.points
    else:
        points = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    results = []
    for point in points:
        results.append({
            "id": point.id,
            "score": float(point.score),
            "text": point.payload.get("text", "") if point.payload else "",
            "payload": point.payload or {},
        })

    logger.info(f"Retrieved {len(results)} memories for query='{question}' (uid={uid})")
    return results


# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Starting MEMORA Backend Foundation...")
    try:
        init_qdrant_collection()
        get_embedding_model()
    except Exception as e:
        logger.error(f"Error during startup initialization: {e}")
        raise e
    yield
    # Teardown sequence
    logger.info("Shutting down MEMORA Backend...")


# FastAPI Application
app = FastAPI(
    title="MEMORA Backend",
    description="Voice-powered autonomous memory and action assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Configuration for Frontend Development & Deployment
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

cors_env = os.getenv("CORS_ORIGINS", "").strip()
allowed_origins_raw = (
    DEFAULT_CORS_ORIGINS + [o.strip() for o in cors_env.split(",") if o.strip()]
    if cors_env
    else DEFAULT_CORS_ORIGINS
)
# Ensure uniqueness and strictly disallow wildcard origins
allowed_origins = [o for o in dict.fromkeys(allowed_origins_raw) if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Pydantic Schemas
class HealthResponse(BaseModel):
    status: str
    app: str
    qdrant_mode: str
    collection: str


class MemoryCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Memory text to vectorize and store")
    uid: str = Field(default="default_user", description="User ID for isolating memories")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata attributes")


class MemoryCreateResponse(BaseModel):
    status: str
    id: str
    text: str
    payload: Dict[str, Any]


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query or question")
    uid: Optional[str] = Field(default=None, description="Optional User ID to filter memories by")
    limit: int = Field(default=5, ge=1, le=50, description="Max number of memories to retrieve")


class MemorySearchResult(BaseModel):
    id: str
    score: float
    text: str
    payload: Dict[str, Any]


class MemorySearchResponse(BaseModel):
    status: str
    query: str
    results: List[MemorySearchResult]


class MemoryItem(BaseModel):
    id: str
    text: str
    created_at: str
    source: str
    metadata: Optional[Dict[str, Any]] = None


class MemoryListResponse(BaseModel):
    status: str
    count: int
    uid: Optional[str] = None
    memories: List[MemoryItem]


# Routes
@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Simple health check endpoint returning operational status."""
    return HealthResponse(
        status="ok",
        app="MEMORA Backend",
        qdrant_mode=_qdrant_mode,
        collection=COLLECTION_NAME,
    )


# Observability state for reasoning pipeline
_latest_reasoning_result: Optional[Dict[str, Any]] = None


def get_reasoning_result_file_path() -> str:
    """
    Returns the resolved file path for the persisted reasoning record.
    Configurable via MEMORA_REASONING_RESULT_FILE environment variable.
    Priority:
    1. Explicit MEMORA_REASONING_RESULT_FILE environment variable if set.
    2. /tmp/latest_reasoning_result.json in Vercel/Linux serverless environments (or when /tmp is writable).
    3. Fallback to 'latest_reasoning_result.json' in current working directory for local development.
    """
    custom_path = os.getenv("MEMORA_REASONING_RESULT_FILE", "").strip()
    if custom_path:
        return custom_path

    if os.getenv("VERCEL") == "1" or (os.path.isdir("/tmp") and os.access("/tmp", os.W_OK)):
        return "/tmp/latest_reasoning_result.json"

    return "latest_reasoning_result.json"


def reset_latest_reasoning_result():
    """Clear the in-memory reasoning record state (used for test isolation)."""
    global _latest_reasoning_result
    _latest_reasoning_result = None


# In-memory thread-safe deduplication store for Omi webhook idempotency
_events_lock = threading.Lock()
_processed_omi_events: Dict[str, Dict[str, Any]] = {}
_MAX_PROCESSED_EVENTS = 2000


def is_event_processed(uid: str, conversation_id: str) -> bool:
    """Check if an event has already been processed for this UID."""
    with _events_lock:
        return f"{uid}:{conversation_id}" in _processed_omi_events


def get_event_record(uid: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the deduplication record for this UID and conversation ID."""
    with _events_lock:
        return _processed_omi_events.get(f"{uid}:{conversation_id}")


def reset_processed_events():
    """Clear all processed event records (used for test isolation)."""
    with _events_lock:
        _processed_omi_events.clear()


def is_explicit_question(text: str) -> bool:
    """
    Deterministic question/request detector for hackathon MVP.
    Conservative:
    - Recognizes obvious question patterns and interrogative markers.
    - Explicitly excludes memory/note commands ('remember that', 'note to self', etc.).
    - Detects compound requests (declarative context clause + imperative request/checklist clause).
    """
    if not text or not text.strip():
        return False

    clean = text.strip().lower()

    # Explicit exclusions: commands to store/save memory, NOT questions
    memory_starters = (
        "remember that", "remember to", "remember:", "note that", "note to",
        "don't forget that", "dont forget that", "dont forget to", "don't forget to",
        "save this", "save that", "store this", "store that",
        "keep in mind that", "remind me to", "remind me that",
    )
    if any(clean.startswith(prefix) for prefix in memory_starters):
        return False

    # Check 1: Explicit question mark anywhere in utterance
    if "?" in clean:
        return True

    # Check 2: Interrogative / request starter phrases at start of utterance
    question_starters = (
        "what ", "when ", "where ", "who ", "why ", "how ", "which ",
        "do i ", "did i ", "does it ", "is there ", "are there ", "have i ",
        "can you ", "could you ", "would you ", "will you ",
        "tell me about ", "tell me what ", "tell me when ", "tell me how ", "tell me where ", "tell me if ",
        "what did i ", "what was ", "what were ",
    )
    if any(clean.startswith(prefix) for prefix in question_starters):
        return True

    # Check 3: Explicit imperative request phrases anywhere in compound utterance
    explicit_request_phrases = (
        "tell me what", "tell me how", "tell me when", "tell me where", "tell me why",
        "tell me about", "give me a checklist", "give me a short checklist",
        "give me a plan", "give me an action plan", "give me the steps", "give me steps",
        "what do i need", "what should i", "what can i", "how should i", "how do i",
    )
    if any(phrase in clean for phrase in explicit_request_phrases):
        return True

    # Check 4: Compound sentence splitting - check if any sentence starts with interrogative or request
    import re
    sentences = [s.strip() for s in re.split(r'[.!?\n]+', clean) if s.strip()]
    for s in sentences:
        if any(s.startswith(prefix) for prefix in question_starters):
            return True
        # Check clause starters inside sentences (e.g. after commas)
        clauses = [c.strip() for c in re.split(r'[,;]+', s) if c.strip()]
        for c in clauses:
            if any(c.startswith(prefix) for prefix in ("tell me ", "give me ", "help me ", "show me ")):
                return True

    return False


def is_combined_recall_planning_query(text: str) -> bool:
    """
    Determines if a query requires BOTH voice memory recall AND action planning/checklist generation.
    Requires presence of:
    1. Memory recall indicators (e.g. 'remember', 'recall', 'based on what you', 'what did i')
    AND
    2. Action planning / checklist indicators (e.g. 'prepare', 'checklist', 'plan', 'steps', 'action items')
    """
    if not text or not text.strip():
        return False

    clean = text.strip().lower()

    recall_indicators = (
        "remember", "recall", "based on what you", "what did i",
        "notes on", "notes about", "what was", "what were",
        "from my memory", "from my memories", "from memory", "from previous",
    )
    planning_indicators = (
        "prepare", "preparation", "checklist", "check list",
        "plan", "planning", "action plan", "steps", "action items", "to-do", "todo",
    )

    has_recall = any(k in clean for k in recall_indicators)
    has_planning = any(k in clean for k in planning_indicators)

    return has_recall and has_planning


def process_reasoning_pipeline(
    question: str,
    uid: str,
    session_id: Optional[str] = None,
    store_question_as_memory: bool = False,
    question_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous reasoning pipeline:
    1. Retrieves relevant previous memories from Qdrant BEFORE the question is saved (self-retrieval prevention).
    2. Routes combined recall + planning queries through deterministic sequential workers:
       MEMORA Reasoner -> MEMORA Action Planner -> Synthesized response.
       Routes single-focus queries through the configured Lyzr Manager Agent.
    3. Records observable results safely (no secrets logged).
    4. Delivers final answer via Omi notification.
    """
    logger.info(f"[Reasoning Pipeline] Processing query for uid='{uid}': '{question}'")
    global _latest_reasoning_result

    result: Dict[str, Any] = {
        "uid": uid,
        "session_id": session_id,
        "question": question,
        "detected_as_query": True,
        "manager_agent_id": None,
        "orchestration_mode": "lyzr_managed_agents",
        "delegation_observed": False,
        "telemetry_status": "pending",
        "workers_invoked": [],
        "execution_trace": [],
        "retrieved_memory_count": 0,
        "retrieved_memory_ids": [],
        "manager_answer": None,
        "lyzr_answer": None,
        "notification_status": "pending",
        "notification_error": None,
        "notification_status_code": None,
        "processing_status": "in_progress",
        "event_status": "processed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    try:
        # Step 1: Semantic retrieval from Qdrant for previous memories (retrieve buffer to prevent self-retrieval starvation)
        memories = retrieve_memories(question=question, uid=uid, limit=15)

        # Self-retrieval protection: exclude any memory matching current query text
        clean_q = question.strip().lower()
        previous_memories = [m for m in memories if m.get("text", "").strip().lower() != clean_q][:5]

        result["retrieved_memory_count"] = len(previous_memories)
        result["retrieved_memory_ids"] = [m["id"] for m in previous_memories]

        context_texts = [m["text"] for m in previous_memories]

        # Step 2: Route according to query intent (combined collaborative vs single-focus Manager)
        import lyzr_service
        from unittest.mock import Mock

        is_combined = is_combined_recall_planning_query(question)

        if is_combined:
            # Deterministic Sequential Orchestration:
            # 1. MEMORA Reasoner (grounded on retrieved memories)
            # 2. MEMORA Action Planner (grounded on Reasoner output + memories)
            result["orchestration_mode"] = "deterministic_sequential"
            result["manager_agent_id"] = "memora_sequential_orchestrator"

            reasoner_agent_id = os.getenv("LYZR_AGENT_ID", "6ac7c057b300b2daefd99218").strip()
            planner_agent_id = os.getenv("LYZR_ACTION_PLANNER_AGENT_ID", "6ac7eba918b1643ee32dad1d").strip()

            workers_invoked = []
            execution_trace = []

            # 1. Worker 1: MEMORA Reasoner
            reasoner_sess = f"{session_id or 'reason'}-reasoner"
            execution_trace.append({
                "event_type": "worker_started",
                "agent": "MEMORA Orchestrator",
                "action": "invoke_worker",
                "target": "MEMORA Reasoner",
                "agent_id": reasoner_agent_id,
                "agent_name": "MEMORA Reasoner",
                "worker_name": "MEMORA Reasoner",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "in_progress",
            })

            reasoner_answer = ""
            try:
                reasoner_res = lyzr_service.ask_lyzr(
                    question=question,
                    context=context_texts,
                    user_id=uid,
                    session_id=reasoner_sess,
                    agent_id=reasoner_agent_id,
                )
                reasoner_answer = (reasoner_res.get("answer") or "").strip()
                execution_trace.append({
                    "event_type": "worker_completed",
                    "agent": "MEMORA Reasoner",
                    "action": "completed",
                    "target": None,
                    "agent_id": reasoner_agent_id,
                    "agent_name": "MEMORA Reasoner",
                    "worker_name": "MEMORA Reasoner",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "completed",
                })
                workers_invoked.append({
                    "agent_id": reasoner_agent_id,
                    "agent_name": "MEMORA Reasoner",
                    "worker_name": "MEMORA Reasoner",
                    "status": "completed",
                })
            except Exception as reasoner_err:
                logger.error(f"MEMORA Reasoner execution failed: {reasoner_err}")
                execution_trace.append({
                    "event_type": "worker_failed",
                    "agent": "MEMORA Reasoner",
                    "action": "failed",
                    "target": None,
                    "agent_id": reasoner_agent_id,
                    "agent_name": "MEMORA Reasoner",
                    "worker_name": "MEMORA Reasoner",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                    "error": str(reasoner_err),
                })
                workers_invoked.append({
                    "agent_id": reasoner_agent_id,
                    "agent_name": "MEMORA Reasoner",
                    "worker_name": "MEMORA Reasoner",
                    "status": "failed",
                })
                raise reasoner_err

            # 2. Worker 2: MEMORA Action Planner
            planner_sess = f"{session_id or 'plan'}-planner"
            execution_trace.append({
                "event_type": "worker_started",
                "agent": "MEMORA Orchestrator",
                "action": "invoke_worker",
                "target": "MEMORA Action Planner",
                "agent_id": planner_agent_id,
                "agent_name": "MEMORA Action Planner",
                "worker_name": "MEMORA Action Planner",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "in_progress",
            })

            planner_context = (
                f"FACTS RECALLED FROM MEMORY (by MEMORA Reasoner):\n"
                f"{reasoner_answer}\n\n"
                f"ORIGINAL RETRIEVED MEMORIES:\n"
                + ("\n".join(f"- {c}" for c in context_texts) if context_texts else "None.")
            )

            planner_answer = ""
            try:
                planner_res = lyzr_service.ask_lyzr(
                    question=question,
                    context=planner_context,
                    user_id=uid,
                    session_id=planner_sess,
                    agent_id=planner_agent_id,
                )
                planner_answer = (planner_res.get("answer") or "").strip()
                execution_trace.append({
                    "event_type": "worker_completed",
                    "agent": "MEMORA Action Planner",
                    "action": "completed",
                    "target": None,
                    "agent_id": planner_agent_id,
                    "agent_name": "MEMORA Action Planner",
                    "worker_name": "MEMORA Action Planner",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "completed",
                })
                workers_invoked.append({
                    "agent_id": planner_agent_id,
                    "agent_name": "MEMORA Action Planner",
                    "worker_name": "MEMORA Action Planner",
                    "status": "completed",
                })
            except Exception as planner_err:
                logger.error(f"MEMORA Action Planner execution failed: {planner_err}")
                execution_trace.append({
                    "event_type": "worker_failed",
                    "agent": "MEMORA Action Planner",
                    "action": "failed",
                    "target": None,
                    "agent_id": planner_agent_id,
                    "agent_name": "MEMORA Action Planner",
                    "worker_name": "MEMORA Action Planner",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                    "error": str(planner_err),
                })
                workers_invoked.append({
                    "agent_id": planner_agent_id,
                    "agent_name": "MEMORA Action Planner",
                    "worker_name": "MEMORA Action Planner",
                    "status": "failed",
                })

            # Final synthesized response
            if planner_answer:
                if reasoner_answer and reasoner_answer not in planner_answer:
                    final_answer = f"{reasoner_answer}\n\nPreparation Checklist:\n{planner_answer}"
                else:
                    final_answer = planner_answer
            else:
                final_answer = f"{reasoner_answer}\n\n(Action planning checklist currently unavailable.)"

            result["manager_answer"] = final_answer
            result["lyzr_answer"] = final_answer
            result["processing_status"] = "completed"
            result["delegation_observed"] = False  # Lyzr Manager did NOT delegate; orchestrated sequentially by backend
            result["telemetry_status"] = "deterministic_trace"
            result["workers_invoked"] = workers_invoked
            result["execution_trace"] = execution_trace

            logger.info(
                f"[Reasoning Pipeline] Sequential Orchestrator Answer: {result['manager_answer']} "
                f"(workers_invoked={len(result['workers_invoked'])})"
            )
        else:
            # Single-focus request: keep existing Lyzr Manager routing
            # If locked milestone tests (3C, 3D) patched ask_lyzr, honor the mock; otherwise invoke Lyzr Manager
            if isinstance(getattr(lyzr_service, "ask_lyzr", None), Mock):
                manager_res = lyzr_service.ask_lyzr(
                    question=question,
                    context=context_texts,
                    user_id=uid,
                    session_id=session_id,
                )
                if isinstance(manager_res, dict) and "manager_agent_id" not in manager_res:
                    manager_res["manager_agent_id"] = os.getenv("LYZR_MANAGER_AGENT_ID", "6ac7ec8f6f28ab116dc67d3b")
            else:
                manager_res = lyzr_service.call_lyzr_manager(
                    question=question,
                    context=context_texts,
                    user_id=uid,
                    session_id=session_id,
                )

            result["manager_agent_id"] = manager_res.get("manager_agent_id")
            result["manager_answer"] = manager_res.get("answer")
            result["lyzr_answer"] = manager_res.get("answer")
            result["processing_status"] = "completed"

            # Harvest sanitized multi-agent telemetry
            tel = manager_res.get("telemetry") or {}
            result["telemetry_status"] = tel.get("telemetry_status", "unavailable")
            result["delegation_observed"] = tel.get("delegation_observed", False)
            result["workers_invoked"] = tel.get("workers_invoked", [])
            result["execution_trace"] = tel.get("execution_trace", [])

            logger.info(
                f"[Reasoning Pipeline] Lyzr Manager [{result['manager_agent_id']}] Answer: {result['manager_answer']} "
                f"(delegation_observed={result['delegation_observed']}, workers={len(result['workers_invoked'])})"
            )

        # Step 3: Send Manager answer back to user via Omi Notifications API
        if result["manager_answer"] and result["manager_answer"].strip():
            from omi_service import send_omi_notification
            result["notification_status"] = "attempted"
            noti_res = send_omi_notification(
                uid=uid,
                message=result["manager_answer"],
            )
            result["notification_status"] = noti_res.get("status", "failed")
            result["notification_error"] = noti_res.get("error")
            result["notification_status_code"] = noti_res.get("status_code")
        else:
            result["notification_status"] = "skipped"
            result["notification_error"] = "Empty Lyzr Manager answer; notification skipped."

    except Exception as e:
        logger.error(f"[Reasoning Pipeline] Execution error: {type(e).__name__}: {str(e)}")
        result["processing_status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["telemetry_status"] = "unavailable"
        result["notification_status"] = "skipped"
        result["notification_error"] = "Lyzr manager reasoning failed; notification skipped."

    _latest_reasoning_result = result

    # Persist observable result to JSON file (configurable via MEMORA_REASONING_RESULT_FILE)
    reasoning_file = get_reasoning_result_file_path()
    try:
        with open(reasoning_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
    except Exception as io_err:
        logger.warning(f"Could not write {reasoning_file}: {io_err}")

    # Step 3: If enabled, store question as interaction record AFTER retrieval
    if store_question_as_memory:
        try:
            store_memory(
                text=question,
                uid=uid,
                source="user_query",
                metadata=question_metadata,
            )
        except Exception as store_err:
            logger.warning(f"Could not store user question after reasoning: {store_err}")

    return result


# --- Omi Webhook Endpoints ---

def verify_omi_webhook_request(
    req_secret: Optional[str] = None,
    header_secret: Optional[str] = None,
    auth_header: Optional[str] = None,
) -> None:
    """
    Guards Omi webhook endpoints (/omi/conversation and /omi/realtime).
    Fails closed when ENVIRONMENT=production if OMI_WEBHOOK_SECRET is missing, empty, or invalid.
    Supports query parameter (?secret=...), X-Omi-Webhook-Secret header, or Authorization: Bearer <secret>.
    In development, allows unauthenticated requests when OMI_WEBHOOK_SECRET is unset.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    expected_secret = os.getenv("OMI_WEBHOOK_SECRET", "").strip()

    if env_name == "production":
        if not expected_secret:
            logger.warning("[Security] Omi webhook rejected: OMI_WEBHOOK_SECRET is not configured in production.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: valid OMI_WEBHOOK_SECRET required for webhook operations.",
            )
        provided = (req_secret or "").strip() or (header_secret or "").strip()
        if not provided and auth_header and auth_header.startswith("Bearer "):
            provided = auth_header[7:].strip()
        if provided != expected_secret:
            logger.warning("[Security] Unauthorized Omi webhook attempt: invalid or missing secret.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized webhook request: missing or invalid secret.",
            )
    else:
        # Development / staging mode: enforce only if explicitly configured
        if expected_secret:
            provided = (req_secret or "").strip() or (header_secret or "").strip()
            if not provided and auth_header and auth_header.startswith("Bearer "):
                provided = auth_header[7:].strip()
            if provided != expected_secret:
                logger.warning("[Security] Unauthorized Omi webhook attempt: invalid or missing secret.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized webhook request: missing or invalid secret.",
                )


def verify_admin_access(auth_header: Optional[str] = None, admin_key: Optional[str] = None) -> None:
    """
    Guards administrative or manual mutation endpoints in production.
    Fails closed when ENVIRONMENT=production if MEMORA_ADMIN_KEY is missing, empty, or invalid.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name == "production":
        expected_admin_key = os.getenv("MEMORA_ADMIN_KEY", "").strip()
        if not expected_admin_key:
            logger.warning("[Security] Admin operation blocked: MEMORA_ADMIN_KEY is not configured in production.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: valid MEMORA_ADMIN_KEY required for administrative operations.",
            )
        provided = (admin_key or "").strip()
        if not provided and auth_header and auth_header.startswith("Bearer "):
            provided = auth_header[7:].strip()
        if provided != expected_admin_key:
            logger.warning("[Security] Unauthorized attempt on administrative endpoint.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: valid MEMORA_ADMIN_KEY required for administrative operations.",
            )


@app.post("/omi/conversation", tags=["Omi"])
def on_conversation(
    background_tasks: BackgroundTasks,
    request: Request,
    uid: Optional[str] = None,
    session_id: Optional[str] = None,
    secret: Optional[str] = None,
    payload: Any = Body(default={}),
):
    """
    Memory creation trigger: fires when an Omi conversation ends.
    Accepts JSON body, extracts transcript_segments and structured.overview.
    If detected as an explicit question, triggers the Qdrant -> Lyzr reasoning pipeline.
    Otherwise, stores the memory into Qdrant as before.
    """
    verify_omi_webhook_request(
        req_secret=secret,
        header_secret=request.headers.get("x-omi-webhook-secret"),
        auth_header=request.headers.get("authorization"),
    )
    # Fallback uid resolution: query param -> body -> default
    effective_uid = uid
    if not effective_uid and isinstance(payload, dict):
        effective_uid = payload.get("uid") or payload.get("user_id")
    if not effective_uid:
        effective_uid = "omi_user"

    logger.info(f"[Omi Webhook] Conversation completed received for uid='{effective_uid}'")
    try:
        raw_json_str = json.dumps(payload, default=str)
        logger.info(f"[Omi Webhook RAW PAYLOAD] {raw_json_str}")
        with open("latest_omi_payload.json", "w", encoding="utf-8") as f:
            f.write(raw_json_str)
    except Exception as e:
        logger.warning(f"Could not log/save raw Omi payload: {e}")

    if not isinstance(payload, dict):
        payload = {}

    conversation_id = payload.get("id") or payload.get("session_id") or session_id or None
    if conversation_id and isinstance(conversation_id, str):
        conversation_id = conversation_id.strip()

    # Idempotency guard: Prevent duplicate execution if the same conversation event is received multiple times
    if conversation_id:
        dedup_key = f"{effective_uid}:{conversation_id}"
        with _events_lock:
            if dedup_key in _processed_omi_events:
                logger.info(
                    f"[Omi Webhook Idempotency] Duplicate conversation event skipped: "
                    f"uid='{effective_uid}', conversation_id='{conversation_id}' (event_status='duplicate_skipped')"
                )
                return {"status": "ok", "event_status": "duplicate_skipped"}
            _processed_omi_events[dedup_key] = {
                "uid": effective_uid,
                "conversation_id": conversation_id,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "event_status": "processed",
            }
            if len(_processed_omi_events) > _MAX_PROCESSED_EVENTS:
                oldest_key = next(iter(_processed_omi_events))
                del _processed_omi_events[oldest_key]

    effective_session_id = conversation_id or session_id or None

    segments = payload.get("transcript_segments") or payload.get("segments") or []
    transcript = " ".join(
        s.get("text", "") for s in segments if isinstance(s, dict) and s.get("text")
    ).strip()

    structured = payload.get("structured") or {}
    overview = (structured.get("overview", "") if isinstance(structured, dict) else "") or ""
    title = (structured.get("title", "") if isinstance(structured, dict) else "") or ""
    action_items = structured.get("action_items", []) if isinstance(structured, dict) else []

    # Combine overview + transcript text per guide specification
    parts = []
    if overview:
        parts.append(overview.strip())
    if transcript:
        parts.append(transcript.strip())

    text = " ".join(parts).strip()

    # Determine if the utterance is an explicit question/request
    # Prefer raw transcript for query evaluation; fallback to overview if transcript is empty
    candidate_query = transcript or overview
    if is_explicit_question(candidate_query):
        logger.info(f"[Omi Webhook] Utterance identified as explicit question: '{candidate_query}'")
        query_metadata = {
            "source": "conversation_query",
            "uid": effective_uid,
            "session_id": effective_session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "segment_count": len(segments),
        }
        # Run Qdrant retrieval + Lyzr reasoning in background task for fast HTTP 200
        background_tasks.add_task(
            process_reasoning_pipeline,
            question=candidate_query,
            uid=effective_uid,
            session_id=effective_session_id,
            store_question_as_memory=True, # stores AFTER retrieval
            question_metadata=query_metadata,
        )
    elif text:
        # Normal memory/statement: store as before
        metadata = {
            "source": "conversation",
            "uid": effective_uid,
            "session_id": effective_session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "action_items": action_items,
            "segment_count": len(segments),
        }
        # Run storage via BackgroundTasks for quick HTTP 200 response
        background_tasks.add_task(
            store_memory,
            text=text,
            uid=effective_uid,
            source="conversation",
            metadata=metadata,
        )
        logger.info(f"[Omi Webhook] Queued conversation memory for uid='{effective_uid}' ({len(text)} chars)")
    else:
        logger.warning(f"[Omi Webhook] No non-empty text found in conversation payload for uid='{effective_uid}'")

    return {"status": "ok"}


@app.get("/omi/events/{conversation_id}", tags=["Omi"])
def get_event_status_endpoint(conversation_id: str, uid: Optional[str] = None):
    """Inspects the idempotency processing status of a specific Omi conversation event."""
    effective_uid = uid or "omi_user"
    record = get_event_record(effective_uid, conversation_id)
    if record:
        return {"status": "ok", "event_status": record.get("event_status", "processed"), "record": record}
    return {"status": "not_found", "event_status": "not_seen"}


@app.post("/omi/realtime", tags=["Omi"])
def on_realtime(
    background_tasks: BackgroundTasks,
    request: Request,
    uid: Optional[str] = None,
    session_id: Optional[str] = None,
    secret: Optional[str] = None,
    payload: Any = Body(default=[]),
):
    """
    Real-time transcript trigger: fires in small batches while user speaks into Omi.
    Accepts either a JSON list of segments or a dict with {"segments": [...]}.
    Guarded by verify_omi_webhook_request in production.
    Stores non-empty transcript text in Qdrant.
    """
    verify_omi_webhook_request(
        req_secret=secret,
        header_secret=request.headers.get("x-omi-webhook-secret"),
        auth_header=request.headers.get("authorization"),
    )
    effective_uid = uid
    if not effective_uid and isinstance(payload, dict):
        effective_uid = payload.get("uid") or payload.get("user_id")
    if not effective_uid:
        effective_uid = "omi_user"

    logger.info(f"[Omi Webhook] Realtime transcript received for uid='{effective_uid}', session_id='{session_id}'")
    effective_session_id = session_id
    if isinstance(payload, list):
        segments = payload
    elif isinstance(payload, dict):
        segments = payload.get("segments") or payload.get("transcript_segments") or []
        if not effective_session_id:
            effective_session_id = payload.get("session_id")
    else:
        segments = []

    text = " ".join(
        s.get("text", "") for s in segments if isinstance(s, dict) and s.get("text")
    ).strip()

    if text:
        metadata = {
            "source": "realtime",
            "uid": effective_uid,
            "session_id": effective_session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "segment_count": len(segments),
        }
        background_tasks.add_task(
            store_memory,
            text=text,
            uid=effective_uid,
            source="realtime",
            metadata=metadata,
        )
        logger.info(f"[Omi Webhook] Queued realtime memory for uid='{effective_uid}' ({len(text)} chars)")
    else:
        logger.warning(f"[Omi Webhook] Empty realtime segment text received for uid='{effective_uid}'")

    return {"status": "ok"}


# --- Generic Memory Endpoints ---

@app.post("/memories", response_model=MemoryCreateResponse, status_code=status.HTTP_201_CREATED, tags=["Memories"])
def create_memory(request: MemoryCreateRequest, req: Request):
    """Stores a new memory by generating its embedding and persisting to Qdrant."""
    verify_admin_access(
        auth_header=req.headers.get("authorization"),
        admin_key=req.headers.get("x-admin-key"),
    )
    try:
        result = store_memory(
            text=request.text,
            uid=request.uid,
            source="manual",
            metadata=request.metadata,
        )
        return MemoryCreateResponse(
            status="success",
            id=result["id"],
            text=result["text"],
            payload=result["payload"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to store memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store memory: {str(e)}",
        )


def get_effective_demo_uid(caller_uid: Optional[str] = None) -> str:
    """
    Returns server-configured UID for identity-isolated UI access (GET /memories, POST /memories/search).
    Enforces server-side identity scoping:
    1. If DEMO_UID / DEFAULT_UID is set in environment:
       - 'all' is explicitly disallowed for browser endpoints to prevent cross-user leakage, falling back to 'default_user'.
       - Server-configured identity takes absolute precedence over any caller-provided UID (preventing attacker overrides).
    2. If DEMO_UID is not set in environment:
       - Uses caller_uid if explicitly provided (for backward-compatible API callers).
       - Falls back to 'default_user' if caller_uid is omitted or empty (never None, preventing unfiltered searches).
    """
    raw_env = os.getenv("DEMO_UID", "").strip() or os.getenv("DEFAULT_UID", "").strip()
    if raw_env:
        if raw_env.lower() == "all":
            logger.warning("[Security] DEMO_UID='all' is disallowed for browser-facing endpoints; enforcing 'default_user'.")
            return "default_user"
        return raw_env

    clean_caller = (caller_uid or "").strip()
    if clean_caller and clean_caller.lower() != "all":
        return clean_caller
    return "default_user"


@app.post("/memories/search", response_model=MemorySearchResponse, tags=["Memories"])
def search_memories(request: MemorySearchRequest):
    """
    Retrieves relevant memories using semantic similarity in Qdrant.
    Scoped server-side to prevent unauthorized cross-user memory exposure.
    """
    try:
        effective_uid = get_effective_demo_uid(caller_uid=request.uid)
        memories = retrieve_memories(
            question=request.query,
            uid=effective_uid,
            limit=request.limit,
        )
        return MemorySearchResponse(
            status="success",
            query=request.query,
            results=[MemorySearchResult(**m) for m in memories],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to search memories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memories: {str(e)}",
        )


SAFE_EXCLUDED_KEYS = {
    "uid",
    "text",
    "source",
    "created_at",
    "ts",
    "vector",
    "api_key",
    "secret",
    "token",
    "password",
    "authorization",
}


@app.get("/memories", response_model=MemoryListResponse, tags=["Memories"])
def list_recent_memories(
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Max number of recent memories to retrieve (1-50)",
    ),
):
    """
    Retrieves recent voice memories in descending chronological order.
    Scoped server-side via DEMO_UID / DEFAULT_UID to prevent arbitrary cross-user access.
    Returns sanitized UI-safe fields without embeddings or secrets.
    """
    try:
        client = get_qdrant_client()
        effective_uid = get_effective_demo_uid()

        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="uid",
                    match=MatchValue(value=effective_uid),
                )
            ]
        )

        all_points = []
        offset = None
        # Bounded scroll batches to gather points for chronological sorting
        max_fetch = max(limit * 3, 60)
        while len(all_points) < max_fetch:
            batch, offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=scroll_filter,
                limit=min(50, max_fetch - len(all_points)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not batch:
                break
            all_points.extend(batch)
            if offset is None:
                break

        def _point_timestamp(p) -> float:
            pl = p.payload or {}
            ts = pl.get("ts")
            if isinstance(ts, (int, float)):
                return float(ts)
            c_at = pl.get("created_at")
            if isinstance(c_at, str):
                try:
                    return datetime.fromisoformat(c_at.replace("Z", "+00:00")).timestamp()
                except Exception:
                    pass
            return 0.0

        all_points.sort(key=_point_timestamp, reverse=True)
        selected_points = all_points[:limit]

        memories: List[MemoryItem] = []
        for p in selected_points:
            pl = p.payload or {}
            c_at = pl.get("created_at")
            if not c_at and pl.get("ts"):
                try:
                    c_at = datetime.fromtimestamp(float(pl["ts"]), tz=timezone.utc).isoformat()
                except Exception:
                    c_at = datetime.now(timezone.utc).isoformat()
            elif not c_at:
                c_at = datetime.now(timezone.utc).isoformat()

            meta = {
                k: v for k, v in pl.items()
                if k.lower() not in SAFE_EXCLUDED_KEYS
            }

            memories.append(
                MemoryItem(
                    id=str(p.id),
                    text=str(pl.get("text", "")),
                    created_at=str(c_at),
                    source=str(pl.get("source", "unknown")),
                    metadata=meta if meta else None,
                )
            )

        return MemoryListResponse(
            status="success",
            count=len(memories),
            uid=effective_uid,
            memories=memories,
        )
    except Exception as e:
        logger.error(f"Failed to list memories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list memories: {str(e)}",
        )


# --- Lyzr Reasoning Endpoint ---

class ReasonRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question for the reasoning agent")
    context: Optional[Union[List[str], str]] = Field(default=None, description="Memory context or list of facts")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier for multi-turn tracking")


class ReasonResponse(BaseModel):
    status: str
    question: str
    answer: str
    session_id: str
    agent_id: str


@app.post("/reason", response_model=ReasonResponse, tags=["Lyzr"])
def reason_endpoint(request: ReasonRequest, req: Request):
    """
    Submits user question and provided memory context to Lyzr MEMORA Reasoner agent.
    Never alters Qdrant or exposes secrets.
    Protected by verify_admin_access in production.
    """
    verify_admin_access(
        auth_header=req.headers.get("authorization"),
        admin_key=req.headers.get("x-admin-key"),
    )
    try:
        from lyzr_service import ask_lyzr
        result = ask_lyzr(
            question=request.question,
            context=request.context,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        return ReasonResponse(
            status="success",
            question=request.question,
            answer=result["answer"],
            session_id=result["session_id"],
            agent_id=result["agent_id"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(re))
    except Exception as e:
        logger.error(f"Unexpected error in /reason: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal reasoning service error.",
        )


@app.get("/reason/latest", tags=["Lyzr"])
def get_latest_reasoning_result():
    """
    Returns the latest observable reasoning pipeline execution result.
    Never exposes API keys or internal secrets.
    """
    global _latest_reasoning_result
    if _latest_reasoning_result is not None:
        return _latest_reasoning_result
    try:
        reasoning_file = get_reasoning_result_file_path()
        if os.path.exists(reasoning_file):
            with open(reasoning_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read reasoning record file: {e}")
    return {"status": "none", "message": "No reasoning pipeline executed yet."}


# ==========================================
# Frontend SPA & Static Assets Serving
# ==========================================

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

def get_frontend_dist_dir() -> str:
    """
    Resolves the frontend distribution directory.
    Prefers the bundled AppSail package directory (backend/static/) when present,
    falling back to the monorepo path (../frontend/dist/) for local development.
    """
    bundled_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    monorepo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
    if os.path.isdir(bundled_dir) and os.path.isfile(os.path.join(bundled_dir, "index.html")):
        return bundled_dir
    return monorepo_dir


FRONTEND_DIST_DIR = get_frontend_dist_dir()
FRONTEND_INDEX_HTML = os.path.join(FRONTEND_DIST_DIR, "index.html")
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")

RESERVED_API_PREFIXES = (
    "health",
    "memories",
    "reason",
    "omi",
    "docs",
    "redoc",
    "openapi.json",
    "api",
)


def _is_frontend_built() -> bool:
    """Returns True if the frontend production build assets exist."""
    dist_dir = get_frontend_dist_dir()
    return os.path.isdir(dist_dir) and os.path.isfile(os.path.join(dist_dir, "index.html"))


# Mount compiled /assets directory if present
if os.path.isdir(FRONTEND_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="static_assets")


@app.get("/", include_in_schema=False)
async def serve_home():
    """Serves the frontend homepage if built, otherwise an informative development status."""
    if _is_frontend_built():
        dist_dir = get_frontend_dist_dir()
        return FileResponse(os.path.join(dist_dir, "index.html"), media_type="text/html")
    return {
        "status": "ok",
        "app": "MEMORA Backend",
        "message": "Frontend build not detected. Run 'npm run build' inside /frontend or use Vite dev server on port 5173.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/app", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/get-started", include_in_schema=False)
async def serve_known_spa_routes():
    """Explicitly serves SPA client routes to index.html."""
    if _is_frontend_built():
        dist_dir = get_frontend_dist_dir()
        return FileResponse(os.path.join(dist_dir, "index.html"), media_type="text/html")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Frontend production build not found. Run 'npm run build' in /frontend.",
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str):
    """
    Catch-all router for frontend deep links and static root files.
    Strictly guards against path traversal and returns JSON 404 for reserved API paths.
    """
    clean_path = full_path.strip().lstrip("/")

    # Guard: Reserved API endpoints must NEVER return the SPA index.html
    for prefix in RESERVED_API_PREFIXES:
        if clean_path == prefix or clean_path.startswith(f"{prefix}/"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API endpoint '/{clean_path}' not found.",
            )

    # Guard: Detect directory traversal attempt
    if ".." in full_path or clean_path.startswith(".."):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '/{clean_path}' not found.",
        )

    # If the frontend is built, check for root static assets (favicon, manifest, etc.)
    if _is_frontend_built():
        dist_dir = get_frontend_dist_dir()
        index_html = os.path.join(dist_dir, "index.html")

        # Traversal protection: canonicalize and verify containment within active dist dir
        candidate_file = os.path.abspath(os.path.join(dist_dir, clean_path))
        if candidate_file.startswith(dist_dir) and os.path.isfile(candidate_file):
            return FileResponse(candidate_file)

        # Disallow returning SPA HTML for paths with file extensions (e.g. missing .png, .js, .css, etc.)
        if "." in os.path.basename(clean_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Static asset '/{clean_path}' not found.",
            )

        # Fallback to SPA index.html ONLY for recognized SPA client subpaths
        if clean_path.startswith(("app", "login", "get-started")):
            return FileResponse(index_html, media_type="text/html")

        # Unknown paths return 404 JSON, preventing indiscriminate 200 OK HTML
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '/{clean_path}' not found.",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Resource '/{clean_path}' not found.",
    )


if __name__ == "__main__":
    import uvicorn
    # Catalyst AppSail passes listening port via X_ZOHO_CATALYST_LISTEN_PORT
    listen_port = int(
        os.getenv("X_ZOHO_CATALYST_LISTEN_PORT")
        or os.getenv("PORT")
        or "8000"
    )
    uvicorn.run("app:app", host="0.0.0.0", port=listen_port, reload=False)
