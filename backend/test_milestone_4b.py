"""
Milestone 4B Test Suite:
Safe Backend Enablement - CORS & Read-Only Recent-Memory Endpoint
Covers CORS headers/preflight, GET /memories schema, bounds, chronological ordering, and identity isolation.
"""

import os
import sys
import time
import unittest
from datetime import datetime, timezone
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
    get_qdrant_client,
    COLLECTION_NAME,
)


class TestMilestone4BBackendEnablement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    # 1. CORS Preflight & Header Verification
    def test_cors_preflight_and_headers_allowed_origin(self):
        """Verify CORS OPTIONS preflight and GET headers for allowed local Vite origin."""
        # Preflight OPTIONS request
        response = self.client.options(
            "/memories",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )
        self.assertEqual(
            response.headers.get("access-control-allow-credentials"),
            "true",
        )

        # Actual GET request with allowed origin
        get_resp = self.client.get(
            "/memories",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(
            get_resp.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:5173",
        )

    def test_cors_disallowed_origin_rejected(self):
        """Verify unauthorized origins do not receive access-control-allow-origin."""
        get_resp = self.client.get(
            "/memories",
            headers={"Origin": "http://malicious-site.example.com"},
        )
        # Endpoint can be reached, but CORS header must NOT authorize the malicious origin
        self.assertNotEqual(
            get_resp.headers.get("access-control-allow-origin"),
            "http://malicious-site.example.com",
        )

    # 2. GET /memories Response Shape & Sanitization
    def test_get_memories_schema_and_sanitization(self):
        """Verify response contains required UI fields and omits embeddings and internal secrets."""
        test_uid = f"user_test_m4b_schema_{int(time.time())}"
        
        # Store test memory with custom metadata
        stored = store_memory(
            text="User's passport expires on November 15, 2029.",
            uid=test_uid,
            source="voice_test",
            metadata={"category": "travel", "confidential_level": 2},
        )
        self.assertIn("id", stored)

        with patch.dict(os.environ, {"DEMO_UID": test_uid}):
            response = self.client.get("/memories")
            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("uid"), test_uid)
            self.assertGreaterEqual(data.get("count"), 1)
            self.assertIsInstance(data.get("memories"), list)

            # Inspect memory item
            item = next((m for m in data["memories"] if m["id"] == stored["id"]), None)
            self.assertIsNotNone(item, "Stored memory was not found in response")
            self.assertEqual(item["text"], "User's passport expires on November 15, 2029.")
            self.assertEqual(item["source"], "voice_test")
            self.assertIn("created_at", item)

            # Ensure metadata is present and sanitized
            self.assertIsNotNone(item.get("metadata"))
            self.assertEqual(item["metadata"].get("category"), "travel")

            # Crucial security check: Ensure no vector embeddings, UIDs, or raw tokens are leaked
            for key in ["vector", "embedding", "uid", "api_key", "secret", "token"]:
                self.assertNotIn(key, item, f"Key '{key}' should not be in memory item root")
                if item.get("metadata"):
                    self.assertNotIn(key, item["metadata"], f"Key '{key}' should not be in memory metadata")

    # 3. Query Limit Bounds (default 20, min 1, max 50)
    def test_get_memories_limit_bounds(self):
        """Verify boundary checking on limit query parameter."""
        test_uid = f"user_test_m4b_bounds_{int(time.time())}"
        for i in range(5):
            store_memory(text=f"Numbered note {i}", uid=test_uid)

        with patch.dict(os.environ, {"DEMO_UID": test_uid}):
            # Valid custom limit
            resp_valid = self.client.get("/memories?limit=3")
            self.assertEqual(resp_valid.status_code, 200)
            self.assertEqual(len(resp_valid.json()["memories"]), 3)

            # Invalid limit: 0 (less than 1)
            resp_low = self.client.get("/memories?limit=0")
            self.assertEqual(resp_low.status_code, 422)

            # Invalid limit: negative
            resp_neg = self.client.get("/memories?limit=-5")
            self.assertEqual(resp_neg.status_code, 422)

            # Invalid limit: 51 (greater than max 50)
            resp_high = self.client.get("/memories?limit=51")
            self.assertEqual(resp_high.status_code, 422)

    # 4. Descending Chronological Ordering
    def test_get_memories_chronological_ordering(self):
        """Verify memories are returned with newest first."""
        test_uid = f"user_test_m4b_chrono_{int(time.time())}"

        # Store older memory
        m1 = store_memory(text="Older memory recorded first", uid=test_uid)
        time.sleep(0.05)
        # Store newer memory
        m2 = store_memory(text="Newer memory recorded second", uid=test_uid)

        with patch.dict(os.environ, {"DEMO_UID": test_uid}):
            response = self.client.get("/memories")
            self.assertEqual(response.status_code, 200)
            memories = response.json()["memories"]

            # Locate indices of both memories
            idx_m1 = next(i for i, m in enumerate(memories) if m["id"] == m1["id"])
            idx_m2 = next(i for i, m in enumerate(memories) if m["id"] == m2["id"])

            # Newer memory (m2) must come before older memory (m1)
            self.assertLess(
                idx_m2,
                idx_m1,
                f"Newer memory m2 (idx={idx_m2}) should precede older memory m1 (idx={idx_m1})"
            )

    # 5. Identity Isolation & Rejection of Client UID Override
    def test_identity_isolation_and_no_browser_uid_override(self):
        """Verify server-side DEMO_UID scoping cannot be overridden by untrusted query parameters."""
        uid_alice = f"user_alice_{int(time.time())}"
        uid_bob = f"user_bob_{int(time.time())}"

        store_memory(text="Alice secret memory: project key is alpha-99", uid=uid_alice)
        store_memory(text="Bob secret memory: favorite dessert is tiramisu", uid=uid_bob)

        # Configure server scope for Alice
        with patch.dict(os.environ, {"DEMO_UID": uid_alice}):
            # Standard request
            resp = self.client.get("/memories")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            texts = [m["text"] for m in data["memories"]]
            self.assertTrue(any("alpha-99" in t for t in texts))
            self.assertFalse(any("tiramisu" in t for t in texts))

            # Attempt untrusted override: pass ?uid=bob
            resp_override = self.client.get(f"/memories?uid={uid_bob}")
            self.assertEqual(resp_override.status_code, 200)
            override_data = resp_override.json()
            override_texts = [m["text"] for m in override_data["memories"]]

            # Must still ONLY contain Alice's memories
            self.assertTrue(any("alpha-99" in t for t in override_texts))
            self.assertFalse(any("tiramisu" in t for t in override_texts), "Bob's memory was leaked via query param!")
            self.assertEqual(override_data["uid"], uid_alice)

    # 6. Empty Result Handling
    def test_empty_memories_for_new_or_empty_uid(self):
        """Verify clean empty response when a user has no memories."""
        empty_uid = f"user_empty_{int(time.time())}"
        with patch.dict(os.environ, {"DEMO_UID": empty_uid}):
            resp = self.client.get("/memories")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["count"], 0)
            self.assertEqual(data["uid"], empty_uid)
            self.assertEqual(data["memories"], [])


if __name__ == "__main__":
    unittest.main()
