import os
import sys
import json
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, retrieve_memories


def run_omi_tests():
    print("=" * 60)
    print("TESTING OMI WEBHOOKS AND USER-ISOLATED RETRIEVAL")
    print("=" * 60)

    client = TestClient(app)

    # 1. Test POST /omi/conversation
    print("\n[TEST 1] Testing POST /omi/conversation with structured transcript...")
    user_id_1 = "omi_user_42"
    conversation_payload = {
        "transcript_segments": [
            {
                "text": "We need to finalize the slides for the Lyzr agent presentation by Friday.",
                "speaker": "SPEAKER_00",
                "is_user": True,
                "start": 0.0,
                "end": 4.2
            },
            {
                "text": "And remember to invite Rahul and Priya to the review call on Thursday 4 PM.",
                "speaker": "SPEAKER_01",
                "is_user": False,
                "start": 4.5,
                "end": 8.1
            }
        ],
        "structured": {
            "title": "Lyzr Presentation Review",
            "overview": "Discussion on finalizing presentation slides and scheduling review call.",
            "action_items": [
                "Finalize slides for Lyzr agent presentation by Friday",
                "Invite Rahul and Priya to review call on Thursday 4 PM"
            ]
        }
    }

    resp = client.post(f"/omi/conversation?uid={user_id_1}", json=conversation_payload)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("[OK] POST /omi/conversation succeeded.")

    # 2. Test POST /omi/realtime
    print("\n[TEST 2] Testing POST /omi/realtime with live transcript chunks...")
    realtime_payload = {
        "segments": [
            {
                "text": "Note to self: the WiFi password for the conference room is Pegasus2026.",
                "speaker": "SPEAKER_00",
                "is_user": True,
                "start": 0.0,
                "end": 3.5
            }
        ]
    }
    resp_rt = client.post(f"/omi/realtime?uid={user_id_1}&session_id=live_sess_99", json=realtime_payload)
    print(f"Status Code: {resp_rt.status_code}")
    print(f"Response: {resp_rt.json()}")
    assert resp_rt.status_code == 200
    assert resp_rt.json()["status"] == "ok"
    print("[OK] POST /omi/realtime succeeded.")

    # 2b. Test 3-Second Real-Time Buffering (Workshop Cell 41)
    print("\n[TEST 2b] Testing 3-second realtime buffering & session flushing (Cell 41)...")
    buffer_sess = "sess_buffered_42"
    resp_chunk1 = client.post(
        f"/omi/realtime?uid={user_id_1}&session_id={buffer_sess}&buffer=1",
        json=[{"text": "Keycard access code for server room"}]
    )
    assert resp_chunk1.status_code == 200
    resp_chunk2 = client.post(
        f"/omi/realtime?uid={user_id_1}&session_id={buffer_sess}&buffer=1",
        json=[{"text": "is entered as 8821 on the keypad."}]
    )
    assert resp_chunk2.status_code == 200
    # Flush session buffer explicitly
    resp_flush = client.post(f"/omi/realtime/flush?uid={user_id_1}&session_id={buffer_sess}")
    assert resp_flush.status_code == 200
    assert resp_flush.json()["status"] == "ok"
    # Verify concatenated memory retrieved
    buf_res = retrieve_memories(question="server room keypad keycard", uid=user_id_1, limit=1)
    assert len(buf_res) > 0
    assert "8821" in buf_res[0]["text"]
    assert "server room" in buf_res[0]["text"]
    print("[OK] Workshop Cell 41 realtime buffering and consolidation verified.")

    # 3. Test Retrieval with UID Filter
    print("\n[TEST 3] Testing semantic retrieval filtered by uid...")
    query = "What is the WiFi password for the conference room?"
    results = retrieve_memories(question=query, uid=user_id_1, limit=3)
    print(f"Query: '{query}' (uid='{user_id_1}')")
    print(f"Found {len(results)} matches:")
    for idx, r in enumerate(results, 1):
        print(f"  [{idx}] Score: {r['score']:.4f} | Source: {r['payload'].get('source')} | Text: {r['text'][:80]}...")
    assert len(results) > 0
    assert "Pegasus2026" in results[0]["text"]
    assert results[0]["score"] > 0.6
    print("[OK] Semantic retrieval matched realtime memory correctly.")

    # 4. Test User Isolation (Different UID must NOT see memories)
    print("\n[TEST 4] Testing user isolation (different UID)...")
    other_user = "unauthorized_user_999"
    isolated_results = retrieve_memories(question=query, uid=other_user, limit=3)
    print(f"Query for other user '{other_user}': {len(isolated_results)} results found.")
    assert len(isolated_results) == 0, f"Expected 0 results for different user, got {len(isolated_results)}"
    print("[OK] User isolation confirmed! Memories are strictly segregated by uid.")

    # 5. Test Action Items retrieval
    print("\n[TEST 5] Testing action item retrieval from conversation webhook...")
    action_query = "Who should be invited to the review call?"
    action_results = retrieve_memories(question=action_query, uid=user_id_1, limit=3)
    print(f"Query: '{action_query}'")
    for idx, r in enumerate(action_results, 1):
        print(f"  [{idx}] Score: {r['score']:.4f} | Text: {r['text'][:80]}...")
    assert len(action_results) > 0
    assert "Rahul and Priya" in action_results[0]["text"]
    print("[OK] Action item semantic retrieval passed.")

    print("\n" + "=" * 60)
    print("ALL OMI WEBHOOK AND RETRIEVAL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_omi_tests()
