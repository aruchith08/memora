"""
Milestone 3D Idempotency Test Suite:
Omi Webhook Idempotency & Duplicate Event Prevention
Covers all 9 required test cases with mocked external calls.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app import (
    app,
    init_qdrant_collection,
    reset_processed_events,
    is_event_processed,
    get_event_record,
)


class TestMilestone3DIdempotency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        reset_processed_events()
        self.mock_env = {
            "OMI_APP_ID": "mock-app-id-dedup",
            "OMI_APP_SECRET": "mock-secret-dedup",
            "LYZR_API_KEY": "mock-lyzr-key",
            "LYZR_AGENT_ID": "mock-agent-id",
        }

    # 1. First event is processed normally
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_1_first_event_processed_normally(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "The secret code is Blue-7429."}
        mock_notif.return_value = {"status": "sent", "uid": "user_idemp_1", "error": None, "status_code": 200}

        conv_id = "conv-first-test-001"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "What is the secret code for the memorial test?"}],
            "structured": {"overview": "Question regarding memorial test code."}
        }

        resp = self.client.post(f"/omi/conversation?uid=user_idemp_1", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

        # Verify recorded state
        self.assertTrue(is_event_processed("user_idemp_1", conv_id))
        rec = get_event_record("user_idemp_1", conv_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["event_status"], "processed")

        # Verify pipeline executed
        mock_lyzr.assert_called_once()
        mock_notif.assert_called_once()

    # 2. Same conversation/event ID sent twice: first processes, second is skipped
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_2_duplicate_event_skipped(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Answer 1"}
        mock_notif.return_value = {"status": "sent", "uid": "user_idemp_2", "error": None, "status_code": 200}

        conv_id = "conv-dupe-test-002"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "What is the meeting time tomorrow?"}],
            "structured": {"overview": "User asked for meeting time."}
        }

        # 1st request
        resp1 = self.client.post(f"/omi/conversation?uid=user_idemp_2", json=payload)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json(), {"status": "ok"})

        # 2nd request (duplicate)
        resp2 = self.client.post(f"/omi/conversation?uid=user_idemp_2", json=payload)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json().get("status"), "ok")
        self.assertEqual(resp2.json().get("event_status"), "duplicate_skipped")

    # 3. Duplicate does not call Lyzr twice
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_3_duplicate_does_not_call_lyzr_twice(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Gate code is 4492"}
        mock_notif.return_value = {"status": "sent", "uid": "user_idemp_3", "error": None, "status_code": 200}

        conv_id = "conv-lyzr-once-003"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "What is the parking gate code?"}],
            "structured": {"overview": "Parking question."}
        }

        # Send three consecutive identical requests
        for _ in range(3):
            resp = self.client.post(f"/omi/conversation?uid=user_idemp_3", json=payload)
            self.assertEqual(resp.status_code, 200)

        # Lyzr should ONLY be called once
        self.assertEqual(mock_lyzr.call_count, 1)

    # 4. Duplicate does not send two Omi notifications
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_4_duplicate_does_not_send_two_notifications(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Password is test1234"}
        mock_notif.return_value = {"status": "sent", "uid": "user_idemp_4", "error": None, "status_code": 200}

        conv_id = "conv-notif-once-004"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "What is the password?"}],
            "structured": {"overview": "Password query."}
        }

        # Send twice
        self.client.post(f"/omi/conversation?uid=user_idemp_4", json=payload)
        self.client.post(f"/omi/conversation?uid=user_idemp_4", json=payload)

        # Notification should ONLY be sent once
        self.assertEqual(mock_notif.call_count, 1)

    # 5. Duplicate normal statement does not create duplicate Qdrant memory
    @patch("app.store_memory")
    def test_5_duplicate_does_not_create_duplicate_memory(self, mock_store):
        conv_id = "conv-memory-once-005"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "Remember that Alice prefers tea over coffee."}],
            "structured": {"overview": "Alice beverage preference."}
        }

        # Send twice
        resp1 = self.client.post(f"/omi/conversation?uid=user_idemp_5", json=payload)
        resp2 = self.client.post(f"/omi/conversation?uid=user_idemp_5", json=payload)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json().get("event_status"), "duplicate_skipped")

        # store_memory should only be called once
        self.assertEqual(mock_store.call_count, 1)

    # 6. Different conversation IDs are processed independently
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_6_different_conversation_ids_processed_independently(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Independent answer"}
        mock_notif.return_value = {"status": "sent", "uid": "user_idemp_6", "error": None, "status_code": 200}

        payload1 = {
            "id": "conv-indep-A",
            "transcript_segments": [{"text": "What is question A?"}],
            "structured": {"overview": "Question A"}
        }
        payload2 = {
            "id": "conv-indep-B",
            "transcript_segments": [{"text": "What is question B?"}],
            "structured": {"overview": "Question B"}
        }

        resp1 = self.client.post("/omi/conversation?uid=user_idemp_6", json=payload1)
        resp2 = self.client.post("/omi/conversation?uid=user_idemp_6", json=payload2)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertIsNone(resp1.json().get("event_status"))
        self.assertIsNone(resp2.json().get("event_status"))

        self.assertEqual(mock_lyzr.call_count, 2)
        self.assertEqual(mock_notif.call_count, 2)

    # 7. UID isolation remains intact (same conversation ID for two different UIDs)
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_7_uid_isolation_with_shared_conversation_id(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Isolated answer"}
        mock_notif.return_value = {"status": "sent", "uid": "user_A", "error": None, "status_code": 200}

        shared_conv_id = "conv-shared-id-007"
        payload = {
            "id": shared_conv_id,
            "transcript_segments": [{"text": "What is my task?"}],
            "structured": {"overview": "Task question"}
        }

        # User A sends event
        resp_a = self.client.post(f"/omi/conversation?uid=user_A", json=payload)
        self.assertEqual(resp_a.status_code, 200)

        # User B sends same conversation ID -> should NOT be skipped because UID is different
        resp_b = self.client.post(f"/omi/conversation?uid=user_B", json=payload)
        self.assertEqual(resp_b.status_code, 200)
        self.assertIsNone(resp_b.json().get("event_status"))

        self.assertEqual(mock_lyzr.call_count, 2)

        # User A sends again -> SHOULD be skipped
        resp_a_dupe = self.client.post(f"/omi/conversation?uid=user_A", json=payload)
        self.assertEqual(resp_a_dupe.json().get("event_status"), "duplicate_skipped")

        # Lyzr still only 2
        self.assertEqual(mock_lyzr.call_count, 2)

    # 8. GET /omi/events/{conversation_id} endpoint returns observable state
    def test_8_observable_event_status_endpoint(self):
        conv_id = "conv-obs-endpoint-008"
        payload = {
            "id": conv_id,
            "transcript_segments": [{"text": "Remember to buy groceries."}],
            "structured": {"overview": "Groceries"}
        }

        # Before sending: not seen
        resp_before = self.client.get(f"/omi/events/{conv_id}?uid=user_obs")
        self.assertEqual(resp_before.status_code, 200)
        self.assertEqual(resp_before.json()["event_status"], "not_seen")

        # Post event
        self.client.post("/omi/conversation?uid=user_obs", json=payload)

        # After sending: processed
        resp_after = self.client.get(f"/omi/events/{conv_id}?uid=user_obs")
        self.assertEqual(resp_after.status_code, 200)
        self.assertEqual(resp_after.json()["event_status"], "processed")
        self.assertEqual(resp_after.json()["record"]["conversation_id"], conv_id)

    # 9. Query param session_id also serves as fallback deduplication key
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_9_session_id_query_param_deduplication(self, mock_notif, mock_lyzr):
        mock_lyzr.return_value = {"answer": "Fallback dedup answer"}
        mock_notif.return_value = {"status": "sent", "uid": "user_sess_param", "error": None, "status_code": 200}

        payload = {
            "transcript_segments": [{"text": "What is the schedule?"}],
            "structured": {"overview": "Schedule query"}
        }

        # Post with session_id query param
        resp1 = self.client.post("/omi/conversation?uid=user_sess_param&session_id=sess_query_009", json=payload)
        resp2 = self.client.post("/omi/conversation?uid=user_sess_param&session_id=sess_query_009", json=payload)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json().get("event_status"), "duplicate_skipped")
        self.assertEqual(mock_lyzr.call_count, 1)


if __name__ == "__main__":
    unittest.main()
