"""
Unit & Integration Tests for MEMORA Unified Deployment Foundation.

Tests:
1. API Route Precedence (/health, /memories, /reason/latest)
2. SPA Route Serving (/, /app, /login, /get-started)
3. Unknown API 404 Guard (never returns index.html)
4. Path Traversal Guard
5. Missing Frontend Build Graceful Fallback
6. Security & Configuration Validation (Qdrant remote enforcement in production, admin protection, webhook secrets)

Safety:
- All tests run in-memory using FastAPI TestClient.
- Uses temporary directory overrides and environment patching.
- Zero mutations to existing Qdrant stores or reasoning result files.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app as memora_app


class TestUnifiedDeployment(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary directory for test reasoning result file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_reason_file = os.path.join(self.temp_dir.name, "test_reason.json")
        self.mock_env = {
            "MEMORA_REASONING_RESULT_FILE": self.test_reason_file,
            "ENVIRONMENT": "development",
            "DEMO_UID": "test_demo_user",
        }
        self.env_patcher = patch.dict(os.environ, self.mock_env)
        self.env_patcher.start()
        self.client = TestClient(memora_app.app)

    def tearDown(self):
        self.env_patcher.stop()
        self.temp_dir.cleanup()

    # 1. API Route Precedence
    def test_1_api_route_precedence(self):
        """Verifies that API endpoints are handled directly and never hijacked by static serving."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/json")
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("app"), "MEMORA Backend")

    # 2. SPA Route Serving
    def test_2_spa_known_routes_serve_html(self):
        """Verifies that known SPA routes return HTML when frontend/dist is built."""
        if not memora_app._is_frontend_built():
            self.skipTest("frontend/dist not present; skipping built SPA serving test")

        for route in ["/", "/app", "/login", "/get-started"]:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.headers.get("content-type", ""))
            self.assertIn("<div id=\"root\">", resp.text)

    # 3. Unknown API 404 Guard
    def test_3_unknown_api_endpoints_return_json_404(self):
        """Verifies that unknown API paths return JSON 404 and NEVER the SPA index.html."""
        for path in ["/api/unknown", "/health/extra", "/memories/fake/route", "/reason/invalid"]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.headers.get("content-type"), "application/json")
            self.assertIn("detail", resp.json())
            self.assertNotIn("<div id=\"root\">", resp.text)

    # 4. Path Traversal Protection
    def test_4_path_traversal_is_blocked(self):
        """Verifies that directory traversal payloads cannot read arbitrary files."""
        # Test directly with relative traversal segments
        resp = self.client.get("/sub/../../etc/passwd")
        self.assertIn(resp.status_code, [404, 400])
        self.assertNotIn("root:x:", resp.text)

        resp2 = self.client.get("/assets/../index.html")
        self.assertIn(resp2.status_code, [404, 400, 200])
        self.assertNotIn("root:x:", resp2.text)

    # 5. Missing Frontend Build Graceful Fallback
    @patch("app._is_frontend_built", return_value=False)
    def test_5_missing_frontend_fallback(self, mock_built):
        """Verifies that when frontend/dist is absent, backend serves an informative JSON status."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("Frontend build not detected", data.get("message", ""))

        resp_app = self.client.get("/app")
        self.assertEqual(resp_app.status_code, 404)
        self.assertEqual(resp_app.headers.get("content-type"), "application/json")

    # 6. Production Remote Qdrant Enforcement
    def test_6_production_remote_qdrant_enforcement(self):
        """Verifies that ENVIRONMENT=production raises RuntimeError if QDRANT_URL is not set."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "QDRANT_URL": ""}, clear=True):
            # Reset client cache
            memora_app._qdrant_client = None
            with self.assertRaises(RuntimeError) as ctx:
                memora_app.get_qdrant_client()
            self.assertIn("QDRANT_URL must be configured when ENVIRONMENT=production", str(ctx.exception))

    # 7. Production Admin Key Protection for Mutations
    def test_7_admin_protection_for_mutations(self):
        """Verifies that POST /memories requires MEMORA_ADMIN_KEY when in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "MEMORA_ADMIN_KEY": "secret-admin-pass"}):
            # Without key
            resp = self.client.post("/memories", json={"text": "Test memory", "uid": "test_user"})
            self.assertEqual(resp.status_code, 401)

            # With wrong key
            resp = self.client.post(
                "/memories",
                headers={"X-Admin-Key": "wrong-key"},
                json={"text": "Test memory", "uid": "test_user"},
            )
            self.assertEqual(resp.status_code, 401)

    def test_7b_admin_protection_fails_closed_when_key_missing_in_production(self):
        """Verifies that operations fail closed when ENVIRONMENT=production and MEMORA_ADMIN_KEY is unset."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "MEMORA_ADMIN_KEY": ""}):
            # POST /memories fails closed
            resp_mem = self.client.post("/memories", json={"text": "Test memory", "uid": "test_user"})
            self.assertEqual(resp_mem.status_code, 401)
            self.assertIn("valid MEMORA_ADMIN_KEY required", resp_mem.json().get("detail", ""))

            # POST /reason fails closed
            resp_reason = self.client.post(
                "/reason",
                json={"question": "What is scheduled?", "user_id": "test_user"},
            )
            self.assertEqual(resp_reason.status_code, 401)
            self.assertIn("valid MEMORA_ADMIN_KEY required", resp_reason.json().get("detail", ""))

    def test_7c_reason_endpoint_production_protection(self):
        """Verifies that POST /reason enforces MEMORA_ADMIN_KEY in production with missing, invalid, and valid keys."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "MEMORA_ADMIN_KEY": "secret-admin-pass"}):
            # 1. Missing credentials -> 401
            resp_no_key = self.client.post(
                "/reason",
                json={"question": "What is scheduled?", "user_id": "test_user"},
            )
            self.assertEqual(resp_no_key.status_code, 401)

            # 2. Invalid credentials -> 401
            resp_bad_key = self.client.post(
                "/reason",
                headers={"X-Admin-Key": "wrong-secret"},
                json={"question": "What is scheduled?", "user_id": "test_user"},
            )
            self.assertEqual(resp_bad_key.status_code, 401)

            # 3. Valid credentials via X-Admin-Key -> allowed
            with patch("lyzr_service.ask_lyzr", return_value={"answer": "Demo answer", "session_id": "s1", "agent_id": "a1"}):
                resp_valid = self.client.post(
                    "/reason",
                    headers={"X-Admin-Key": "secret-admin-pass"},
                    json={"question": "What is scheduled?", "user_id": "test_user"},
                )
                self.assertEqual(resp_valid.status_code, 200)
                self.assertEqual(resp_valid.json().get("answer"), "Demo answer")

            # 4. Valid credentials via Authorization Bearer header -> allowed
            with patch("lyzr_service.ask_lyzr", return_value={"answer": "Demo answer", "session_id": "s1", "agent_id": "a1"}):
                resp_bearer = self.client.post(
                    "/reason",
                    headers={"Authorization": "Bearer secret-admin-pass"},
                    json={"question": "What is scheduled?", "user_id": "test_user"},
                )
                self.assertEqual(resp_bearer.status_code, 200)

    def test_7d_development_mode_allows_unauthenticated_requests(self):
        """Verifies that local development mode does not block /reason requests."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "MEMORA_ADMIN_KEY": ""}):
            with patch("lyzr_service.ask_lyzr", return_value={"answer": "Dev answer", "session_id": "s_dev", "agent_id": "a_dev"}):
                resp = self.client.post(
                    "/reason",
                    json={"question": "Dev test question", "user_id": "dev_user"},
                )
                self.assertEqual(resp.status_code, 200)

    # 8. Webhook Secret Protection for Both Omi Ingestion Routes
    def test_8a_omi_webhooks_fail_closed_when_secret_unset_in_production(self):
        """Verifies that both /omi/conversation and /omi/realtime fail closed when secret is unset in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OMI_WEBHOOK_SECRET": ""}):
            # /omi/conversation fails closed
            resp_conv = self.client.post("/omi/conversation?uid=test_uid", json={"id": "test-prod-1"})
            self.assertEqual(resp_conv.status_code, 401)
            self.assertIn("valid OMI_WEBHOOK_SECRET required", resp_conv.json().get("detail", ""))

            # /omi/realtime fails closed
            resp_rt = self.client.post("/omi/realtime?uid=test_uid", json=[{"text": "realtime chunk"}])
            self.assertEqual(resp_rt.status_code, 401)
            self.assertIn("valid OMI_WEBHOOK_SECRET required", resp_rt.json().get("detail", ""))

    def test_8b_omi_webhooks_missing_and_invalid_credentials_in_production(self):
        """Verifies that missing and invalid credentials are rejected on both Omi endpoints."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OMI_WEBHOOK_SECRET": "test-wh-secret-999"}):
            # Missing credentials
            resp_conv_no_sec = self.client.post("/omi/conversation?uid=test_uid", json={"id": "test-1"})
            self.assertEqual(resp_conv_no_sec.status_code, 401)

            resp_rt_no_sec = self.client.post("/omi/realtime?uid=test_uid", json=[{"text": "chunk"}])
            self.assertEqual(resp_rt_no_sec.status_code, 401)

            # Invalid credentials via query param
            resp_conv_bad = self.client.post("/omi/conversation?uid=test_uid&secret=wrong-secret", json={"id": "test-1"})
            self.assertEqual(resp_conv_bad.status_code, 401)

            resp_rt_bad = self.client.post("/omi/realtime?uid=test_uid&secret=wrong-secret", json=[{"text": "chunk"}])
            self.assertEqual(resp_rt_bad.status_code, 401)

            # Invalid credentials via header
            resp_conv_bad_hdr = self.client.post(
                "/omi/conversation?uid=test_uid",
                headers={"X-Omi-Webhook-Secret": "wrong-secret"},
                json={"id": "test-1"},
            )
            self.assertEqual(resp_conv_bad_hdr.status_code, 401)

            resp_rt_bad_hdr = self.client.post(
                "/omi/realtime?uid=test_uid",
                headers={"X-Omi-Webhook-Secret": "wrong-secret"},
                json=[{"text": "chunk"}],
            )
            self.assertEqual(resp_rt_bad_hdr.status_code, 401)

    def test_8c_omi_webhooks_valid_credentials_via_all_supported_mechanisms(self):
        """Verifies that valid credentials succeed via query param, header, and Bearer token."""
        secret_val = "test-wh-secret-999"
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "OMI_WEBHOOK_SECRET": secret_val}):
            # 1. Valid via URL query parameter (?secret=...)
            with patch("app.is_explicit_question", return_value=False), patch("app.store_memory"):
                resp_conv_q = self.client.post(
                    f"/omi/conversation?uid=test_uid&secret={secret_val}",
                    json={"id": "test-ok-1", "transcript_segments": [{"text": "Hello note."}]},
                )
                self.assertEqual(resp_conv_q.status_code, 200)

                resp_rt_q = self.client.post(
                    f"/omi/realtime?uid=test_uid&secret={secret_val}",
                    json=[{"text": "Streaming voice chunk"}],
                )
                self.assertEqual(resp_rt_q.status_code, 200)

            # 2. Valid via X-Omi-Webhook-Secret header
            with patch("app.is_explicit_question", return_value=False), patch("app.store_memory"):
                resp_conv_hdr = self.client.post(
                    "/omi/conversation?uid=test_uid",
                    headers={"X-Omi-Webhook-Secret": secret_val},
                    json={"id": "test-ok-2", "transcript_segments": [{"text": "Hello note 2."}]},
                )
                self.assertEqual(resp_conv_hdr.status_code, 200)

                resp_rt_hdr = self.client.post(
                    "/omi/realtime?uid=test_uid",
                    headers={"X-Omi-Webhook-Secret": secret_val},
                    json=[{"text": "Streaming voice chunk 2"}],
                )
                self.assertEqual(resp_rt_hdr.status_code, 200)

            # 3. Valid via Authorization: Bearer <secret>
            with patch("app.is_explicit_question", return_value=False), patch("app.store_memory"):
                resp_conv_bearer = self.client.post(
                    "/omi/conversation?uid=test_uid",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    json={"id": "test-ok-3", "transcript_segments": [{"text": "Hello note 3."}]},
                )
                self.assertEqual(resp_conv_bearer.status_code, 200)

                resp_rt_bearer = self.client.post(
                    "/omi/realtime?uid=test_uid",
                    headers={"Authorization": f"Bearer {secret_val}"},
                    json=[{"text": "Streaming voice chunk 3"}],
                )
                self.assertEqual(resp_rt_bearer.status_code, 200)

    def test_8d_omi_webhooks_development_mode_allows_unauthenticated_requests(self):
        """Verifies that development mode allows unauthenticated Omi webhook ingestion when secret is unset."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "OMI_WEBHOOK_SECRET": ""}):
            with patch("app.is_explicit_question", return_value=False), patch("app.store_memory"):
                resp_conv = self.client.post(
                    "/omi/conversation?uid=test_uid",
                    json={"id": "test-dev-1", "transcript_segments": [{"text": "Dev note."}]},
                )
                self.assertEqual(resp_conv.status_code, 200)

                resp_rt = self.client.post(
                    "/omi/realtime?uid=test_uid",
                    json=[{"text": "Dev streaming chunk"}],
                )
                self.assertEqual(resp_rt.status_code, 200)


    # 9. Bundled Static Packaging Verification
    def test_9_bundled_static_packaging_verification(self):
        """Verifies that backend/static packaging is preferred and bundles index.html and assets."""
        bundled_static = os.path.join(backend_dir, "static")
        self.assertTrue(os.path.isdir(bundled_static), "backend/static/ must exist after packaging")
        self.assertTrue(
            os.path.isfile(os.path.join(bundled_static, "index.html")),
            "backend/static/index.html must exist in the AppSail bundle",
        )
        self.assertTrue(
            os.path.isdir(os.path.join(bundled_static, "assets")),
            "backend/static/assets must exist in the AppSail bundle",
        )
        self.assertEqual(memora_app.get_frontend_dist_dir(), bundled_static)

    # 10. FastEmbed Cache Path Resolution
    def test_10_fastembed_cache_path_resolution(self):
        """Verifies that get_fastembed_cache_path resolves appropriately for env and serverless."""
        # Case A: Explicit FASTEMBED_CACHE_PATH env var
        with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": "/custom/cache/dir"}):
            self.assertEqual(memora_app.get_fastembed_cache_path(), "/custom/cache/dir")

        # Case B: Serverless environment detected (VERCEL=1)
        with patch.dict(os.environ, {"FASTEMBED_CACHE_PATH": "", "VERCEL": "1"}):
            self.assertEqual(memora_app.get_fastembed_cache_path(), "/tmp/fastembed_cache")

    # 11. Reasoning Result Path Resolution
    def test_11_reasoning_result_path_resolution(self):
        """Verifies that get_reasoning_result_file_path resolves appropriately for env and serverless."""
        # Case A: Explicit MEMORA_REASONING_RESULT_FILE
        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": "/custom/path/result.json"}):
            self.assertEqual(memora_app.get_reasoning_result_file_path(), "/custom/path/result.json")

        # Case B: Serverless environment detected (VERCEL=1)
        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": "", "VERCEL": "1"}):
            self.assertEqual(memora_app.get_reasoning_result_file_path(), "/tmp/latest_reasoning_result.json")


    # 12. Payload Index Initialization Creates Index
    def test_12_payload_index_initialization_creates_index(self):
        """Verifies that init_qdrant_collection calls create_payload_index for 'uid'."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = memora_app.COLLECTION_NAME
        mock_client.get_collections.return_value.collections = [mock_collection]

        with patch("app.get_qdrant_client", return_value=mock_client):
            memora_app.init_qdrant_collection()
            mock_client.create_payload_index.assert_called_once_with(
                collection_name=memora_app.COLLECTION_NAME,
                field_name="uid",
                field_schema=memora_app.PayloadSchemaType.KEYWORD,
            )

    # 13. Payload Index Idempotent On Existing
    def test_13_payload_index_idempotent_on_existing(self):
        """Verifies that init_qdrant_collection handles already existing index gracefully."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = memora_app.COLLECTION_NAME
        mock_client.get_collections.return_value.collections = [mock_collection]
        mock_client.create_payload_index.side_effect = Exception("Index already exists for uid")

        with patch("app.get_qdrant_client", return_value=mock_client):
            # Should not raise exception
            try:
                memora_app.init_qdrant_collection()
            except Exception as e:
                self.fail(f"init_qdrant_collection raised unexpectedly on existing index: {e}")


    # 14. Delete Memory Success (Owner)
    def test_14_delete_memory_success(self):
        """Verifies that an authorized user can delete their own memory record."""
        mock_client = MagicMock()
        mock_point = MagicMock()
        mock_point.id = "mem-123"
        mock_point.payload = {"uid": "test_demo_user", "text": "Test memory to delete"}
        mock_client.retrieve.return_value = [mock_point]

        with patch("app.get_qdrant_client", return_value=mock_client):
            resp = self.client.delete("/memories/mem-123")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("id"), "mem-123")
            mock_client.delete.assert_called_once_with(
                collection_name=memora_app.COLLECTION_NAME,
                points_selector=["mem-123"],
            )

    # 15. Delete Memory Not Found
    def test_15_delete_memory_not_found(self):
        """Verifies that attempting to delete a non-existent point returns 404."""
        mock_client = MagicMock()
        mock_client.retrieve.return_value = []

        with patch("app.get_qdrant_client", return_value=mock_client):
            resp = self.client.delete("/memories/non-existent-id")
            self.assertEqual(resp.status_code, 404)
            self.assertIn("not found", resp.json().get("detail", ""))

    # 16. Delete Memory Cross-User Forbidden
    def test_16_delete_memory_cross_user_forbidden(self):
        """Verifies that attempting to delete another user's memory returns 403 Forbidden."""
        mock_client = MagicMock()
        mock_point = MagicMock()
        mock_point.id = "mem-other-456"
        mock_point.payload = {"uid": "victim_user", "text": "Victim's private memory"}
        mock_client.retrieve.return_value = [mock_point]

        with patch("app.get_qdrant_client", return_value=mock_client):
            resp = self.client.delete("/memories/mem-other-456")
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Forbidden", resp.json().get("detail", ""))
            mock_client.delete.assert_not_called()

    # 17. Delete Memory Production Admin Key Enforcement
    def test_17_delete_memory_production_admin_required(self):
        """Verifies that in production, DELETE /memories/{id} requires valid MEMORA_ADMIN_KEY."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "MEMORA_ADMIN_KEY": "secret-admin-pass"}):
            # Attempt without key
            resp_no_key = self.client.delete("/memories/mem-123")
            self.assertEqual(resp_no_key.status_code, 401)

            # Attempt with wrong key
            resp_wrong_key = self.client.delete("/memories/mem-123", headers={"X-Admin-Key": "wrong"})
            self.assertEqual(resp_wrong_key.status_code, 401)


if __name__ == "__main__":
    unittest.main()

