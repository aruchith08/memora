"""
Regression and isolation tests for MEMORA reasoning record persistence.
Verifies:
1. Default path resolution defaults to 'latest_reasoning_result.json'.
2. Custom MEMORA_REASONING_RESULT_FILE is respected for both reading and writing.
3. Empty/whitespace MEMORA_REASONING_RESULT_FILE safely falls back to default.
4. Mocked test reasoning pipelines write only to the configured isolated file.
5. Project-level production reasoning record remains untouched.
6. GET /reason/latest returns the fallback record from the configured file when in-memory state is None.
"""

import os
import sys
import json
import uuid
import tempfile
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
    get_reasoning_result_file_path,
    reset_latest_reasoning_result,
    process_reasoning_pipeline,
    init_qdrant_collection,
    reset_processed_events,
)


class TestReasoningIsolation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        reset_processed_events()
        reset_latest_reasoning_result()

    def tearDown(self):
        reset_latest_reasoning_result()

    # 1. Default file path backward compatibility
    def test_default_file_path_backward_compatible(self):
        """When MEMORA_REASONING_RESULT_FILE is unset, resolves to latest_reasoning_result.json."""
        with patch.dict(os.environ, {}, clear=False):
            if "MEMORA_REASONING_RESULT_FILE" in os.environ:
                del os.environ["MEMORA_REASONING_RESULT_FILE"]
            resolved = get_reasoning_result_file_path()
            self.assertEqual(resolved, "latest_reasoning_result.json")

    # 2. Whitespace-only or empty string safely falls back to default
    def test_whitespace_or_empty_path_falls_back_to_default(self):
        """When MEMORA_REASONING_RESULT_FILE is empty or whitespace, defaults safely."""
        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": "   "}):
            self.assertEqual(get_reasoning_result_file_path(), "latest_reasoning_result.json")
        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": ""}):
            self.assertEqual(get_reasoning_result_file_path(), "latest_reasoning_result.json")

    # 3. Explicitly configured path is used
    def test_explicitly_configured_path_used(self):
        """When MEMORA_REASONING_RESULT_FILE is set, returns the exact configured path."""
        custom_path = os.path.join(tempfile.gettempdir(), f"custom_reason_{uuid.uuid4().hex[:6]}.json")
        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": custom_path}):
            self.assertEqual(get_reasoning_result_file_path(), custom_path)

    # 4. Mocked test pipeline writes only to configured isolated file and does not modify production file
    def test_mocked_pipeline_writes_only_to_isolated_file(self):
        """Pipeline execution with configured isolation writes to isolated file, preserving production file."""
        prod_path = "latest_reasoning_result.json"
        original_prod_content = None
        if os.path.exists(prod_path):
            with open(prod_path, "r", encoding="utf-8") as f:
                original_prod_content = f.read()

        temp_dir = tempfile.mkdtemp()
        isolated_file = os.path.join(temp_dir, f"isolated_reason_{uuid.uuid4().hex[:8]}.json")

        test_uid = f"user_isolation_{uuid.uuid4().hex[:6]}"
        conv_id = f"conv_isolation_{uuid.uuid4().hex[:6]}"

        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": isolated_file}), \
             patch("lyzr_service.call_lyzr_manager") as mock_manager, \
             patch("omi_service.send_omi_notification") as mock_noti:

            mock_manager.return_value = {
                "answer": "Isolated test mock answer.",
                "session_id": conv_id,
                "manager_agent_id": "test_manager_id",
                "user_id": test_uid,
                "telemetry": {
                    "telemetry_status": "mocked",
                    "delegation_observed": False,
                    "workers_invoked": [],
                    "execution_trace": [],
                },
            }
            mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}

            result = process_reasoning_pipeline(
                question="Where is the isolated testing ground?",
                uid=test_uid,
                session_id=conv_id,
                store_question_as_memory=False,
            )

            self.assertEqual(result["manager_answer"], "Isolated test mock answer.")

            # Verify isolated file exists and contains the test result
            self.assertTrue(os.path.exists(isolated_file), "Isolated file was not created!")
            with open(isolated_file, "r", encoding="utf-8") as f:
                written_data = json.load(f)
            self.assertEqual(written_data.get("manager_answer"), "Isolated test mock answer.")
            self.assertEqual(written_data.get("uid"), test_uid)

            # Crucial verification: Production file must NOT have changed!
            if original_prod_content is not None:
                with open(prod_path, "r", encoding="utf-8") as f:
                    current_prod_content = f.read()
                self.assertEqual(
                    current_prod_content,
                    original_prod_content,
                    "Production latest_reasoning_result.json was altered by isolated test run!",
                )

        # Cleanup isolated file
        if os.path.exists(isolated_file):
            os.remove(isolated_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    # 5. GET /reason/latest reads from configured isolated file when in-memory state is cleared
    def test_get_reason_latest_reads_from_configured_file_when_memory_cleared(self):
        """Endpoint falls back to reading the configured isolated file if in-memory result is None."""
        temp_dir = tempfile.mkdtemp()
        isolated_file = os.path.join(temp_dir, f"isolated_fallback_{uuid.uuid4().hex[:8]}.json")

        payload = {
            "uid": "user_fallback_test",
            "session_id": "sess-fallback-99",
            "question": "Fallback question from file?",
            "manager_answer": "Fallback answer read from isolated file.",
            "processing_status": "completed",
        }
        with open(isolated_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        # Reset in-memory cache to force reading from disk
        reset_latest_reasoning_result()

        with patch.dict(os.environ, {"MEMORA_REASONING_RESULT_FILE": isolated_file}):
            resp = self.client.get("/reason/latest")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("manager_answer"), "Fallback answer read from isolated file.")
            self.assertEqual(data.get("uid"), "user_fallback_test")

        # Cleanup
        if os.path.exists(isolated_file):
            os.remove(isolated_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


if __name__ == "__main__":
    unittest.main()
