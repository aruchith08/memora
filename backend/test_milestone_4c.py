"""
Milestone 4C Test Suite:
Memory Search Identity Isolation
Verifies consistent server-side identity scoping across GET /memories and POST /memories/search,
rejection of cross-user overrides, and preservation of internal Omi UID isolation.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app import (
    app,
    init_qdrant_collection,
    store_memory,
    get_effective_demo_uid,
)


class TestMilestone4CSearchIdentityIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    # 1. Search with no UID remains scoped to configured demo identity
    def test_search_with_no_uid_scoped_to_demo_identity(self):
        """When UID is omitted in POST /memories/search, search scopes to DEMO_UID, never all users."""
        demo_uid = f"user_m4c_demo_{int(time.time())}"
        other_uid = f"user_m4c_other_{int(time.time())}"

        # Store memories for both
        store_memory(text="Alice favorite project is Project Bluebird", uid=demo_uid)
        store_memory(text="Bob favorite project is Project Phoenix", uid=other_uid)

        with patch.dict(os.environ, {"DEMO_UID": demo_uid}):
            resp = self.client.post(
                "/memories/search",
                json={"query": "What is the favorite project?", "limit": 5},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            texts = [r["text"] for r in data["results"]]

            # Must contain Alice's memory and NOT Bob's memory
            self.assertTrue(any("Project Bluebird" in t for t in texts))
            self.assertFalse(any("Project Phoenix" in t for t in texts))

    # 2. Search with attacker-supplied UID cannot access another identity's memories
    def test_search_attacker_supplied_uid_cannot_access_other_memories(self):
        """When an attacker supplies another user's UID, the endpoint refuses the override."""
        demo_uid = f"user_m4c_victim_{int(time.time())}"
        attacker_target_uid = f"user_m4c_secret_vault_{int(time.time())}"

        store_memory(text="Victim user note: buy milk and bread", uid=demo_uid)
        store_memory(text="Secret vault code is Omega-7733", uid=attacker_target_uid)

        with patch.dict(os.environ, {"DEMO_UID": demo_uid}):
            # Attacker passes UID of the secret vault
            resp = self.client.post(
                "/memories/search",
                json={
                    "query": "What is the secret vault code?",
                    "uid": attacker_target_uid,
                    "limit": 5,
                },
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            texts = [r["text"] for r in data["results"]]

            # Must NOT expose the secret vault memory
            self.assertFalse(
                any("Omega-7733" in t for t in texts),
                "Security violation: Attacker-supplied UID leaked another user's memory!",
            )

    # 3. Search with explicit matching UID behaves according to documented contract
    def test_search_with_explicit_matching_uid(self):
        """When caller passes explicit UID that matches server identity, returns expected results."""
        demo_uid = f"user_m4c_matching_{int(time.time())}"
        store_memory(text="Flight AA123 departs at 10:30 PM", uid=demo_uid)

        with patch.dict(os.environ, {"DEMO_UID": demo_uid}):
            resp = self.client.post(
                "/memories/search",
                json={
                    "query": "When does flight AA123 depart?",
                    "uid": demo_uid,
                    "limit": 2,
                },
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertTrue(len(data["results"]) > 0)
            self.assertIn("AA123", data["results"][0]["text"])

    # 4. GET /memories and POST /memories/search use consistent identity scoping
    def test_consistent_identity_scoping_between_get_and_post(self):
        """Verify GET /memories and POST /memories/search query the exact same user identity."""
        demo_uid = f"user_m4c_consistent_{int(time.time())}"
        other_uid = f"user_m4c_unrelated_{int(time.time())}"

        store_memory(text="Key card color is silver", uid=demo_uid)
        store_memory(text="Key card color is gold", uid=other_uid)

        with patch.dict(os.environ, {"DEMO_UID": demo_uid}):
            # GET /memories
            get_resp = self.client.get("/memories")
            self.assertEqual(get_resp.status_code, 200)
            get_texts = [m["text"] for m in get_resp.json()["memories"]]
            self.assertTrue(any("silver" in t for t in get_texts))
            self.assertFalse(any("gold" in t for t in get_texts))

            # POST /memories/search
            post_resp = self.client.post(
                "/memories/search",
                json={"query": "What color is the key card?", "limit": 5},
            )
            self.assertEqual(post_resp.status_code, 200)
            post_texts = [r["text"] for r in post_resp.json()["results"]]
            self.assertTrue(any("silver" in t for t in post_texts))
            self.assertFalse(any("gold" in t for t in post_texts))

    # 5. DEMO_UID=all is safely rejected for browser-facing endpoints
    def test_demo_uid_all_safely_rejected(self):
        """Setting DEMO_UID='all' falls back to 'default_user' and never allows unfiltered searches."""
        with patch.dict(os.environ, {"DEMO_UID": "all"}):
            resolved = get_effective_demo_uid()
            self.assertEqual(resolved, "default_user")

            # GET /memories uses 'default_user'
            get_resp = self.client.get("/memories")
            self.assertEqual(get_resp.status_code, 200)
            self.assertEqual(get_resp.json()["uid"], "default_user")

            # POST /memories/search uses 'default_user'
            post_resp = self.client.post(
                "/memories/search",
                json={"query": "test query", "limit": 2},
            )
            self.assertEqual(post_resp.status_code, 200)

    # 6. Internal Omi reasoning uses the actual incoming Omi UID and remains isolated
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_internal_omi_retrieval_uses_actual_omi_uid(self, mock_notif, mock_lyzr):
        """Omi events retrieve memories for their actual effective Omi UID, not forced to DEMO_UID."""
        mock_lyzr.return_value = {"answer": "You parked on floor 3."}
        mock_notif.return_value = {"status": "sent"}

        omi_real_user = f"user_omi_real_{int(time.time())}"
        demo_user = f"user_demo_env_{int(time.time())}"

        # Store memory for the real Omi user
        store_memory(text="I parked my car on floor 3 in space 304.", uid=omi_real_user)
        # Store unrelated memory for demo user
        store_memory(text="I parked my car in the basement.", uid=demo_user)

        with patch.dict(os.environ, {"DEMO_UID": demo_user}):
            payload = {
                "id": f"conv-omi-m4c-{int(time.time())}",
                "transcript_segments": [{"text": "Where did I park my car?"}],
                "structured": {"overview": "User asked where they parked."},
            }
            # Incoming Omi conversation webhook with uid=omi_real_user
            resp = self.client.post(f"/omi/conversation?uid={omi_real_user}", json=payload)
            self.assertEqual(resp.status_code, 200)

            # In TestClient, BackgroundTasks run synchronously before return
            mock_lyzr.assert_called_once()
            call_kwargs = mock_lyzr.call_args[1]

            # Lyzr must have received memories for the actual Omi user (floor 3) and NOT the demo user (basement)
            context = call_kwargs.get("context") or []
            self.assertTrue(any("floor 3" in c for c in context), f"Expected floor 3 in context, got: {context}")
            self.assertFalse(any("basement" in c for c in context), f"Demo user context leaked into Omi reasoning: {context}")
            self.assertEqual(call_kwargs.get("user_id"), omi_real_user)


if __name__ == "__main__":
    unittest.main()
