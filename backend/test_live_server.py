import subprocess
import time
import sys
import json
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=" * 60)
    print("LAUNCHING LIVE UVICORN SERVER AND RUNNING E2E HTTP TESTS")
    print("=" * 60)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for server to come up
        print("Waiting for uvicorn server to bind to port 8000...")
        healthy = False
        for attempt in range(30):
            time.sleep(1)
            try:
                r = requests.get(f"{SERVER_URL}/health", timeout=2)
                if r.status_code == 200:
                    healthy = True
                    print(f"[OK] Live server became ready in ~{attempt + 1}s!")
                    break
            except Exception:
                pass

        if not healthy:
            print("[ERROR] Server failed to start within 30 seconds.")
            return 1

        # Test 1: GET /health
        print("\n1. Testing GET /health...")
        health_res = requests.get(f"{SERVER_URL}/health")
        print(f"Status Code: {health_res.status_code}")
        print(f"Response: {json.dumps(health_res.json(), indent=2)}")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"
        print("[OK] Live /health passed.")

        # Test 2: POST /memories
        print("\n2. Testing POST /memories...")
        payload = {
            "text": "Live test memory: Alex mentioned that the hackathon demo is scheduled for Sunday at 3 PM",
            "metadata": {"speaker": "Alex", "event": "Hackathon Demo"}
        }
        create_res = requests.post(f"{SERVER_URL}/memories", json=payload)
        print(f"Status Code: {create_res.status_code}")
        print(f"Response: {json.dumps(create_res.json(), indent=2)}")
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["status"] == "success"
        print("[OK] Live POST /memories passed.")

        # Test 3: POST /memories/search
        print("\n3. Testing POST /memories/search...")
        search_payload = {
            "query": "When is the hackathon demo scheduled?",
            "limit": 3
        }
        search_res = requests.post(f"{SERVER_URL}/memories/search", json=search_payload)
        print(f"Status Code: {search_res.status_code}")
        print(f"Response: {json.dumps(search_res.json(), indent=2)}")
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert search_data["status"] == "success"
        assert len(search_data["results"]) > 0
        top = search_data["results"][0]
        print(f"Top Hit Text: {top['text']}")
        print(f"Similarity Score: {top['score']:.4f}")
        assert "Sunday at 3 PM" in top["text"]
        assert top["score"] > 0.6
        print("[OK] Live POST /memories/search passed.")

        # Test 4: Live POST /omi/conversation
        print("\n4. Testing Live POST /omi/conversation...")
        omi_live_payload = {
            "transcript_segments": [
                {"text": "Project MEMORA submitted to the hackathon platform successfully.", "speaker": "SPEAKER_00"}
            ],
            "structured": {
                "title": "Submission Update",
                "overview": "MEMORA project submission status."
            }
        }
        omi_conv_res = requests.post(f"{SERVER_URL}/omi/conversation?uid=live_tester", json=omi_live_payload)
        print(f"Status Code: {omi_conv_res.status_code}")
        print(f"Response: {omi_conv_res.json()}")
        assert omi_conv_res.status_code == 200
        assert omi_conv_res.json()["status"] == "ok"
        print("[OK] Live POST /omi/conversation passed.")

        # Give background task 1 second to write
        time.sleep(1.5)

        # Test 5: Verify retrieval of live Omi memory
        print("\n5. Testing Live Search of Omi Memory...")
        omi_search_res = requests.post(
            f"{SERVER_URL}/memories/search",
            json={"query": "Was MEMORA submitted?", "uid": "live_tester", "limit": 2}
        )
        print(f"Status Code: {omi_search_res.status_code}")
        omi_data = omi_search_res.json()
        assert omi_search_res.status_code == 200
        assert len(omi_data["results"]) > 0
        print(f"Top Hit Text: {omi_data['results'][0]['text']}")
        print(f"Top Hit Score: {omi_data['results'][0]['score']:.4f}")
        assert "MEMORA submitted" in omi_data["results"][0]["text"]
        print("[OK] Live Omi memory stored and retrieved successfully.")

        print("\n" + "=" * 60)
        print("ALL LIVE HTTP SERVER TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return 0

    finally:
        print("\nTerminating live server process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        print("[OK] Server process stopped cleanly.")


if __name__ == "__main__":
    sys.exit(main())
