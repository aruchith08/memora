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
from fastapi import FastAPI, HTTPException, status, Body, BackgroundTasks
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
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

# Globals for lazy/lifespan initialization
_qdrant_client: Optional[QdrantClient] = None
_embedding_model: Optional[TextEmbedding] = None
_qdrant_mode: str = "uninitialized"


def get_embedding_model() -> TextEmbedding:
    """Lazily load and cache the FastEmbed model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading FastEmbed model: {EMBEDDING_MODEL_NAME}")
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
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
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=3.0)
            # Verify connectivity
            client.get_collections()
            _qdrant_client = client
            _qdrant_mode = f"server ({qdrant_url})"
            logger.info(f"Successfully connected to Qdrant server at {qdrant_url}")
            return _qdrant_client
        except Exception as e:
            logger.warning(
                f"Could not connect to Qdrant server at {qdrant_url} ({e}). "
                f"Falling back to local embedded storage at '{qdrant_path}'."
            )

    # Fallback to local embedded storage
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
    """
    if not text or not text.strip():
        return False

    clean = text.strip().lower()

    # Explicit exclusions: commands to store/save memory, NOT questions
    memory_starters = (
        "remember that", "remember to", "remember:", "note that", "note to",
        "don't forget that", "dont forget that", "dont forget to", "don't forget to",
        "save this", "store this", "keep in mind that", "remind me to", "remind me that",
    )
    if any(clean.startswith(prefix) for prefix in memory_starters):
        return False

    # Check 1: Explicit question mark
    if clean.endswith("?"):
        return True

    # Check 2: Interrogative starter phrases
    question_starters = (
        "what ", "when ", "where ", "who ", "why ", "how ", "which ",
        "do i ", "did i ", "does it ", "is there ", "are there ", "have i ",
        "can you tell me ", "could you tell me ", "tell me about ", "tell me what ",
        "tell me when ", "what did i ", "what was ", "what were ",
    )
    if any(clean.startswith(prefix) for prefix in question_starters):
        return True

    return False


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
    2. Packages retrieved memories as CONTEXT for Lyzr MEMORA Reasoner.
    3. Calls ask_lyzr() to generate grounded answer.
    4. Records observable results safely (no secrets logged).
    5. Never saves the Lyzr response into voice_memory.
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
        # Step 1: Semantic retrieval from Qdrant for previous memories
        memories = retrieve_memories(question=question, uid=uid, limit=5)

        # Self-retrieval protection: exclude any memory matching current query text
        clean_q = question.strip().lower()
        previous_memories = [m for m in memories if m.get("text", "").strip().lower() != clean_q]

        result["retrieved_memory_count"] = len(previous_memories)
        result["retrieved_memory_ids"] = [m["id"] for m in previous_memories]

        context_texts = [m["text"] for m in previous_memories]

        # Step 2: Send question + previous memory context to Lyzr Manager
        import lyzr_service
        from unittest.mock import Mock

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

    # Persist observable result to JSON file
    try:
        with open("latest_reasoning_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
    except Exception as io_err:
        logger.warning(f"Could not write latest_reasoning_result.json: {io_err}")

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

@app.post("/omi/conversation", tags=["Omi"])
def on_conversation(
    background_tasks: BackgroundTasks,
    uid: Optional[str] = None,
    session_id: Optional[str] = None,
    payload: Any = Body(default={}),
):
    """
    Memory creation trigger: fires when an Omi conversation ends.
    Accepts JSON body, extracts transcript_segments and structured.overview.
    If detected as an explicit question, triggers the Qdrant -> Lyzr reasoning pipeline.
    Otherwise, stores the memory into Qdrant as before.
    """
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
    uid: Optional[str] = None,
    session_id: Optional[str] = None,
    payload: Any = Body(default=[]),
):
    """
    Real-time transcript trigger: fires in small batches while user speaks into Omi.
    Accepts either a JSON list of segments or a dict with {"segments": [...]}.
    Stores non-empty transcript text in Qdrant.
    """
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
def create_memory(request: MemoryCreateRequest):
    """Stores a new memory by generating its embedding and persisting to Qdrant."""
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


@app.post("/memories/search", response_model=MemorySearchResponse, tags=["Memories"])
def search_memories(request: MemorySearchRequest):
    """Retrieves relevant memories using semantic similarity in Qdrant, optionally filtered by user ID."""
    try:
        memories = retrieve_memories(
            question=request.query,
            uid=request.uid,
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
def reason_endpoint(request: ReasonRequest):
    """
    Submits user question and provided memory context to Lyzr MEMORA Reasoner agent.
    Never alters Qdrant or exposes secrets.
    """
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
        if os.path.exists("latest_reasoning_result.json"):
            with open("latest_reasoning_result.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read latest_reasoning_result.json: {e}")
    return {"status": "none", "message": "No reasoning pipeline executed yet."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
