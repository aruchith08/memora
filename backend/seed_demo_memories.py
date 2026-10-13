"""
MEMORA Synthetic Demo Memory Seeding Script.

Populates a target remote Qdrant collection with high-quality synthetic demo memories
scoped strictly to DEMO_UID (default: 'memora_demo_user').

SAFETY GUARANTEES:
1. STRICTLY REQUIRES QDRANT_URL to be set to a remote server (e.g. Qdrant Cloud).
2. REFUSES TO RUN against local embedded disk storage (./qdrant_storage).
3. Uses deterministic UUIDs derived from a synthetic seed namespace to ensure idempotency.
4. NEVER copies, reads, exports, or touches private local user memories.
"""

import os
import sys
import uuid
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv

# Load backend .env if present
backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(backend_dir, ".env"))
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("memora-seed")

# Deterministic UUID Namespace for Synthetic Demo Data
SYNTHETIC_NAMESPACE = uuid.UUID("a3b4c5d6-e7f8-4901-b234-c5d6e7f8a9b0")

DEMO_MEMORIES: List[Dict[str, Any]] = [
    {
        "id_key": "memora_demo_msf_course",
        "text": "Motorcycle Safety Foundation (MSF) class is scheduled for tomorrow at 9:00 AM at the Safety Training Center. Need to bring helmet, gloves, boots, and driver's license.",
        "category": "schedule",
        "source": "conversation",
    },
    {
        "id_key": "memora_demo_team_standup",
        "text": "Weekly engineering standup: We decided to deploy the unified FastAPI and React build to Render by Tuesday evening. Alex is handling deployment, Jordan is preparing demo slides.",
        "category": "meeting",
        "source": "conversation",
    },
    {
        "id_key": "memora_demo_lecture_notes",
        "text": "Distributed systems lecture note: Vector databases like Qdrant use HNSW indexing for approximate nearest neighbor search, providing sub-millisecond similarity recall at scale.",
        "category": "learning",
        "source": "conversation",
    },
    {
        "id_key": "memora_demo_grocery_reminder",
        "text": "Reminder to pick up groceries after work: almond milk, dark roast coffee beans, and fresh blueberries.",
        "category": "reminder",
        "source": "conversation",
    },
    {
        "id_key": "memora_demo_flight_booking",
        "text": "Flight to San Francisco for the AI Hackathon summit departs on Thursday at 7:45 AM from Terminal 2, Confirmation code SF7892.",
        "category": "travel",
        "source": "conversation",
    },
]


def run_seed():
    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
    target_uid = os.getenv("DEMO_UID", "memora_demo_user").strip()
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "voice_memory").strip()

    # Safety Guard: Require explicit remote Qdrant configuration
    if not qdrant_url or "localhost" in qdrant_url or "127.0.0.1" in qdrant_url:
        logger.error(
            "[Safety Error] Seeding requires an explicit remote Qdrant URL (e.g. Qdrant Cloud). "
            "Refusing to execute against local embedded storage or localhost."
        )
        sys.exit(1)

    logger.info(f"Targeting remote Qdrant cluster: {qdrant_url}")
    logger.info(f"Target collection: '{collection_name}' | Scoped Demo UID: '{target_uid}'")

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from fastembed import TextEmbedding

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=10.0)

    # Initialize collection if missing
    if not client.collection_exists(collection_name):
        logger.info(f"Collection '{collection_name}' does not exist on remote cluster. Creating (384-dim, COSINE)...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        logger.info(f"Collection '{collection_name}' created successfully.")
    else:
        logger.info(f"Collection '{collection_name}' already exists on remote cluster.")

    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    points = []
    for item in DEMO_MEMORIES:
        # Generate deterministic UUID
        point_id = str(uuid.uuid5(SYNTHETIC_NAMESPACE, item["id_key"]))
        embedding = next(iter(embedder.embed([item["text"]]))).tolist()
        payload = {
            "uid": target_uid,
            "text": item["text"],
            "source": item["source"],
            "category": item["category"],
            "is_synthetic_demo": True,
        }
        points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Successfully seeded {len(points)} deterministic synthetic demo memories into '{collection_name}'.")


if __name__ == "__main__":
    run_seed()
