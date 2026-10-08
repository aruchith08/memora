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


def run_milestone_2a_tests():
    print("=" * 70)
    print("RUNNING MILESTONE 2A: OMI WEBHOOK INGESTION LAYER VERIFICATION")
    print("=" * 70)

    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. Test POST /omi/conversation with Guide Structure
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing POST /omi/conversation with simulated Guide payload...")
    uid_1 = "test_user_alpha"
    conv_payload = {
        "transcript_segments": [
            {
                "text": "I need to send the invoice to Rahul by Friday and book the venue on Monday.",
                "speaker": "SPEAKER_0",
                "is_user": True,
                "start": 0.0,
                "end": 4.5
            }
        ],
        "structured": {
            "title": "Action Items",
            "overview": "Discussion regarding sending invoices and venue booking.",
            "action_items": [
                "Send invoice to Rahul by Friday",
                "Book the venue on Monday"
            ]
        }
    }
    resp1 = client.post(f"/omi/conversation?uid={uid_1}&session_id=sess_conv_101", json=conv_payload)
    print(f"Status Code: {resp1.status_code}")
    print(f"Response: {resp1.json()}")
    assert resp1.status_code == 200
    assert resp1.json() == {"status": "ok"}
    print("[OK] /omi/conversation returned 200 OK.")

    # -------------------------------------------------------------
    # 2. Test POST /omi/realtime - Case A (JSON list of segments)
    # -------------------------------------------------------------
    print("\n[TEST 2A] Testing POST /omi/realtime with JSON list payload...")
    rt_list_payload = [
        {"text": "The gate code for the parking lot is 4492.", "speaker": "SPEAKER_0", "is_user": True},
        {"text": "Make sure to park on the second floor.", "speaker": "SPEAKER_0", "is_user": True}
    ]
    resp2a = client.post(f"/omi/realtime?uid={uid_1}&session_id=sess_rt_201", json=rt_list_payload)
    print(f"Status Code: {resp2a.status_code}")
    print(f"Response: {resp2a.json()}")
    assert resp2a.status_code == 200
    assert resp2a.json() == {"status": "ok"}
    print("[OK] /omi/realtime with list payload returned 200 OK.")

    # -------------------------------------------------------------
    # 3. Test POST /omi/realtime - Case B ({"segments": [...]})
    # -------------------------------------------------------------
    print("\n[TEST 2B] Testing POST /omi/realtime with dict {'segments': [...]} payload...")
    rt_dict_payload = {
        "segments": [
            {"text": "Doctor appointment rescheduled to Wednesday at 2 PM.", "speaker": "SPEAKER_1"}
        ]
    }
    resp2b = client.post(f"/omi/realtime?uid={uid_1}&session_id=sess_rt_202", json=rt_dict_payload)
    print(f"Status Code: {resp2b.status_code}")
    print(f"Response: {resp2b.json()}")
    assert resp2b.status_code == 200
    assert resp2b.json() == {"status": "ok"}
    print("[OK] /omi/realtime with segments dict returned 200 OK.")

    # -------------------------------------------------------------
    # 4. Verify Retrieval through existing search functionality
    # -------------------------------------------------------------
    print("\n[TEST 3] Verifying retrieval of ingested Omi memories...")
    # 4a. Check conversation memory retrieval
    q1 = "When do I need to send the invoice to Rahul?"
    res1 = retrieve_memories(question=q1, uid=uid_1, limit=3)
    print(f"Query: '{q1}'")
    assert len(res1) > 0, "Expected to retrieve conversation memory"
    print(f"Top Hit Text: {res1[0]['text']}")
    print(f"Score: {res1[0]['score']:.4f}")
    assert "invoice to Rahul" in res1[0]["text"]
    assert res1[0]["payload"]["source"] == "conversation"
    assert res1[0]["payload"]["uid"] == uid_1
    assert "timestamp" in res1[0]["payload"]
    print("[OK] Conversation memory verified with correct metadata and semantic relevance.")

    # 4b. Check realtime memory retrieval
    q2 = "What is the parking lot gate code?"
    res2 = retrieve_memories(question=q2, uid=uid_1, limit=3)
    print(f"\nQuery: '{q2}'")
    assert len(res2) > 0, "Expected to retrieve realtime memory"
    print(f"Top Hit Text: {res2[0]['text']}")
    print(f"Score: {res2[0]['score']:.4f}")
    assert "4492" in res2[0]["text"]
    assert res2[0]["payload"]["source"] == "realtime"
    assert res2[0]["payload"]["session_id"] == "sess_rt_201"
    print("[OK] Realtime memory verified with session_id and source metadata.")

    # -------------------------------------------------------------
    # 5. UID Metadata Isolation
    # -------------------------------------------------------------
    print("\n[TEST 4] Verifying strict UID metadata isolation...")
    uid_unauthorized = "intruder_user_999"
    isolated_hits = retrieve_memories(question="parking lot gate code", uid=uid_unauthorized, limit=5)
    print(f"Hits for unauthorized uid '{uid_unauthorized}': {len(isolated_hits)}")
    assert len(isolated_hits) == 0, f"Expected 0 hits for different user, got {len(isolated_hits)}"
    print("[OK] User isolation confirmed: no memories leaked across UIDs.")

    # -------------------------------------------------------------
    # 6. Empty Transcript Handling
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing empty transcript handling...")
    # Empty conversation
    empty_conv = {"transcript_segments": [], "structured": {"overview": ""}}
    resp_empty_conv = client.post(f"/omi/conversation?uid={uid_1}", json=empty_conv)
    assert resp_empty_conv.status_code == 200
    assert resp_empty_conv.json() == {"status": "ok"}

    # Empty realtime list
    resp_empty_rt1 = client.post(f"/omi/realtime?uid={uid_1}", json=[])
    assert resp_empty_rt1.status_code == 200
    assert resp_empty_rt1.json() == {"status": "ok"}

    # Realtime with whitespace only
    resp_empty_rt2 = client.post(f"/omi/realtime?uid={uid_1}", json={"segments": [{"text": "   "}]})
    assert resp_empty_rt2.status_code == 200
    assert resp_empty_rt2.json() == {"status": "ok"}
    print("[OK] Empty and whitespace-only payloads handled gracefully with 200 OK.")

    # -------------------------------------------------------------
    # 7. Malformed / Minimal Payload Handling
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing malformed / minimal payload handling...")
    # Minimal empty object
    resp_min = client.post(f"/omi/conversation?uid={uid_1}", json={})
    assert resp_min.status_code == 200
    assert resp_min.json() == {"status": "ok"}

    # Segments not a list
    resp_bad_seg = client.post(f"/omi/conversation?uid={uid_1}", json={"transcript_segments": "corrupted_string"})
    assert resp_bad_seg.status_code == 200
    assert resp_bad_seg.json() == {"status": "ok"}

    # Structured not a dict
    resp_bad_struct = client.post(f"/omi/conversation?uid={uid_1}", json={"structured": 12345})
    assert resp_bad_struct.status_code == 200
    assert resp_bad_struct.json() == {"status": "ok"}

    # Non-dict items inside segments
    resp_bad_items = client.post(f"/omi/realtime?uid={uid_1}", json={"segments": [None, 42, "string_item"]})
    assert resp_bad_items.status_code == 200
    assert resp_bad_items.json() == {"status": "ok"}
    print("[OK] Malformed and corrupt payload structures handled safely without exceptions.")

    # -------------------------------------------------------------
    # 8. Test via FastAPI /memories/search HTTP endpoint
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing search via HTTP endpoint POST /memories/search...")
    search_resp = client.post(
        "/memories/search",
        json={"query": "When is the doctor appointment?", "uid": uid_1, "limit": 2}
    )
    assert search_resp.status_code == 200
    s_data = search_resp.json()
    assert s_data["status"] == "success"
    assert len(s_data["results"]) > 0
    print(f"Top Hit: {s_data['results'][0]['text']}")
    print(f"Score: {s_data['results'][0]['score']:.4f}")
    assert "Wednesday at 2 PM" in s_data["results"][0]["text"]
    print("[OK] HTTP /memories/search endpoint confirmed functional with UID filtering.")

    print("\n" + "=" * 70)
    print("ALL MILESTONE 2A TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_milestone_2a_tests()
