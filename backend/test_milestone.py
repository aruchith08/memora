import os
import sys
import json

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient

# Ensure app can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    app,
    store_memory,
    retrieve_memories,
    init_qdrant_collection,
    get_qdrant_client,
    COLLECTION_NAME,
    VECTOR_DIM,
)


def run_tests():
    print("=" * 60)
    print("STARTING MEMORA BACKEND FOUNDATION TESTS")
    print("=" * 60)

    # 1. Initialize Collection & Vector DB
    print("\n[TEST 1] Initializing Qdrant collection...")
    init_qdrant_collection()
    client = get_qdrant_client()
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    print(f"Collection status: {collection_info.status}")
    print(f"Vectors size: {collection_info.config.params.vectors.size}")
    print(f"Distance metric: {collection_info.config.params.vectors.distance}")
    assert collection_info.config.params.vectors.size == VECTOR_DIM, f"Expected {VECTOR_DIM}, got {collection_info.config.params.vectors.size}"
    print("[OK] Collection successfully initialized with 384 dimensions and Cosine distance.")

    # 2. Test direct store_memory utility
    print("\n[TEST 2] Testing direct memory storage utility...")
    sample_text = "I have an important product meeting tomorrow with the Lyzr engineering team at 10 AM."
    sample_meta = {"source": "unit_test", "category": "meeting"}
    stored_result = store_memory(text=sample_text, metadata=sample_meta)
    print(f"Stored Memory ID: {stored_result['id']}")
    print(f"Stored Text: {stored_result['text']}")
    print(f"Payload: {stored_result['payload']}")
    assert stored_result["id"] is not None
    assert stored_result["text"] == sample_text
    print("[OK] Direct store_memory utility passed.")

    # 3. Test direct retrieve_memories utility
    print("\n[TEST 3] Testing direct memory retrieval utility...")
    query = "When is my meeting with Lyzr?"
    retrieved = retrieve_memories(question=query, limit=2)
    print(f"Query: '{query}'")
    print(f"Retrieved {len(retrieved)} memories:")
    for idx, mem in enumerate(retrieved, start=1):
        print(f"  [{idx}] Score: {mem['score']:.4f} | ID: {mem['id']}")
        print(f"      Text: {mem['text']}")
    assert len(retrieved) > 0, "No memories retrieved"
    assert "Lyzr" in retrieved[0]["text"]
    assert retrieved[0]["score"] > 0.5, f"Expected high cosine similarity, got {retrieved[0]['score']}"
    print(f"[OK] Direct retrieve_memories utility passed with score {retrieved[0]['score']:.4f}.")

    # 4. Test FastAPI endpoints with TestClient
    print("\n[TEST 4] Testing FastAPI HTTP endpoints...")
    with TestClient(app) as test_client:
        # 4a. Health check endpoint
        print("\n--> Testing GET /health...")
        health_resp = test_client.get("/health")
        print(f"Status Code: {health_resp.status_code}")
        print(f"Response: {json.dumps(health_resp.json(), indent=2)}")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "ok"
        assert health_data["app"] == "MEMORA Backend"
        print("[OK] GET /health passed.")

        # 4b. Store memory endpoint
        print("\n--> Testing POST /memories...")
        create_payload = {
            "text": "Remember that Sarah prefers green tea with honey over coffee.",
            "metadata": {"speaker": "Alex", "source": "voice_transcript"}
        }
        create_resp = test_client.post("/memories", json=create_payload)
        print(f"Status Code: {create_resp.status_code}")
        print(f"Response: {json.dumps(create_resp.json(), indent=2)}")
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        assert created_data["status"] == "success"
        assert "Sarah" in created_data["text"]
        print("[OK] POST /memories passed.")

        # 4c. Search memory endpoint
        print("\n--> Testing POST /memories/search...")
        search_payload = {
            "query": "What beverage does Sarah like to drink?",
            "limit": 3
        }
        search_resp = test_client.post("/memories/search", json=search_payload)
        print(f"Status Code: {search_resp.status_code}")
        print(f"Response: {json.dumps(search_resp.json(), indent=2)}")
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert search_data["status"] == "success"
        assert len(search_data["results"]) > 0
        top_hit = search_data["results"][0]
        print(f"Top Hit Text: {top_hit['text']}")
        print(f"Top Hit Score: {top_hit['score']:.4f}")
        assert "Sarah prefers green tea" in top_hit["text"]
        assert top_hit["score"] > 0.5
        print("[OK] POST /memories/search passed.")

    print("\n" + "=" * 60)
    print("ALL MILESTONE 1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
