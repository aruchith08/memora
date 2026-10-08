"""
Milestone 3D Test Suite:
Omi Notification Response via Official Integrations API
Covers all 11 required test cases with 100% mocked HTTP requests.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from app import (
    app,
    process_reasoning_pipeline,
    store_memory,
    init_qdrant_collection,
)
from omi_service import send_omi_notification, get_omi_notification_config


class TestMilestone3D(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        self.mock_env = {
            "OMI_APP_ID": "mock-app-id-12345",
            "OMI_APP_SECRET": "mock-secret-xyz6789",
            "LYZR_API_KEY": "mock-lyzr-key",
            "LYZR_AGENT_ID": "mock-agent-id",
        }

    # 1. Successful notification
    def test_1_successful_notification(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_post.return_value = mock_resp

                res = send_omi_notification(
                    uid="user_123",
                    message="Your MSF class is tomorrow at 9 AM.",
                )

                self.assertEqual(res["status"], "sent")
                self.assertIsNone(res["error"])
                self.assertEqual(res["status_code"], 200)

                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer mock-secret-xyz6789")
                self.assertEqual(kwargs["params"]["uid"], "user_123")
                self.assertEqual(kwargs["params"]["message"], "Your MSF class is tomorrow at 9 AM.")

    # 2. Non-2xx Omi response
    def test_2_non_2xx_omi_response(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 401
                mock_post.return_value = mock_resp

                res = send_omi_notification(
                    uid="user_123",
                    message="Test message",
                )

                self.assertEqual(res["status"], "failed")
                self.assertIn("HTTP 401", res["error"])
                self.assertEqual(res["status_code"], 401)
                # Ensure secret is not in error string
                self.assertNotIn("mock-secret-xyz6789", str(res))

    # 3. Network/timeout failure
    def test_3_network_timeout_failure(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
                res = send_omi_notification(
                    uid="user_123",
                    message="Test message",
                )
                self.assertEqual(res["status"], "failed")
                self.assertIn("timed out", res["error"])

            with patch("requests.post", side_effect=requests.ConnectionError("Network down")):
                res = send_omi_notification(
                    uid="user_123",
                    message="Test message",
                )
                self.assertEqual(res["status"], "failed")
                self.assertIn("network error", res["error"])

    # 4. Missing OMI_APP_ID
    def test_4_missing_omi_app_id(self):
        incomplete_env = {
            "OMI_APP_ID": "",
            "OMI_APP_SECRET": "mock-secret-xyz6789",
        }
        with patch.dict(os.environ, incomplete_env, clear=True):
            res = send_omi_notification(uid="user_123", message="Test")
            self.assertEqual(res["status"], "failed")
            self.assertIn("OMI_APP_ID", res["error"])

    # 5. Missing OMI_APP_SECRET
    def test_5_missing_omi_app_secret(self):
        incomplete_env = {
            "OMI_APP_ID": "mock-app-id-12345",
            "OMI_APP_SECRET": "",
        }
        with patch.dict(os.environ, incomplete_env, clear=True):
            res = send_omi_notification(uid="user_123", message="Test")
            self.assertEqual(res["status"], "failed")
            self.assertIn("OMI_APP_SECRET", res["error"])

    # 6. Correct uid is used in pipeline
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr")
    def test_6_correct_uid_used_in_pipeline(self, mock_ask_lyzr, mock_send_notif):
        mock_ask_lyzr.return_value = {"answer": "You have MSF class tomorrow."}
        mock_send_notif.return_value = {"status": "sent", "uid": "target_user_uid_888", "error": None}

        result = process_reasoning_pipeline(
            question="What class do I have tomorrow?",
            uid="target_user_uid_888",
            session_id="sess_888",
        )

        self.assertEqual(result["processing_status"], "completed")
        self.assertEqual(result["notification_status"], "sent")
        mock_send_notif.assert_called_once()
        self.assertEqual(mock_send_notif.call_args[1]["uid"], "target_user_uid_888")

    # 7. Correct Lyzr answer is sent to Omi notification
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr")
    def test_7_correct_lyzr_answer_sent(self, mock_ask_lyzr, mock_send_notif):
        expected_answer = "Your flight departs at 6:30 PM from terminal 2."
        mock_ask_lyzr.return_value = {"answer": expected_answer}
        mock_send_notif.return_value = {"status": "sent", "uid": "user_travel", "error": None}

        result = process_reasoning_pipeline(
            question="What time is my flight?",
            uid="user_travel",
        )

        mock_send_notif.assert_called_once_with(
            uid="user_travel",
            message=expected_answer,
        )
        self.assertEqual(result["lyzr_answer"], expected_answer)

    # 8. No notification on normal memory statements
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr")
    def test_8_no_notification_on_normal_statements(self, mock_ask_lyzr, mock_send_notif):
        payload = {
            "transcript_segments": [{"text": "I completed my quarterly report today."}],
            "structured": {"overview": "Quarterly report completion log."}
        }

        response = self.client.post("/omi/conversation?uid=statement_user", json=payload)
        self.assertEqual(response.status_code, 200)

        # Neither Lyzr nor Omi notification should be invoked
        mock_ask_lyzr.assert_not_called()
        mock_send_notif.assert_not_called()

    # 9. No notification when Lyzr fails
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr", side_effect=RuntimeError("Lyzr model error"))
    def test_9_no_notification_when_lyzr_fails(self, mock_ask_lyzr, mock_send_notif):
        result = process_reasoning_pipeline(
            question="When is my appointment?",
            uid="fail_user",
        )

        self.assertEqual(result["processing_status"], "error")
        self.assertEqual(result["notification_status"], "skipped")
        self.assertIn("skipped", result["notification_error"])
        mock_send_notif.assert_not_called()

    # 10. Existing reasoning result remains observable
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr")
    def test_10_observable_result_includes_notification_fields(self, mock_ask_lyzr, mock_send_notif):
        mock_ask_lyzr.return_value = {"answer": "Meeting is on Wednesday at 10 AM."}
        mock_send_notif.return_value = {"status": "sent", "uid": "obs_user", "error": None, "status_code": 200}

        payload = {
            "transcript_segments": [{"text": "When is my meeting?"}],
            "structured": {"overview": "User asked meeting time."}
        }

        response = self.client.post("/omi/conversation?uid=obs_user", json=payload)
        self.assertEqual(response.status_code, 200)

        obs_res = self.client.get("/reason/latest")
        self.assertEqual(obs_res.status_code, 200)
        data = obs_res.json()

        self.assertEqual(data["detected_as_query"], True)
        self.assertEqual(data["processing_status"], "completed")
        self.assertEqual(data["notification_status"], "sent")
        self.assertIn("Wednesday at 10 AM", data["lyzr_answer"])

    # 11. Existing UID isolation remains intact
    @patch("omi_service.send_omi_notification")
    @patch("lyzr_service.ask_lyzr")
    def test_11_uid_isolation_with_notifications(self, mock_ask_lyzr, mock_send_notif):
        mock_ask_lyzr.return_value = {"answer": "No relevant info found."}
        mock_send_notif.return_value = {"status": "sent", "uid": "user_two", "error": None}

        # User One stores private note
        store_memory(
            text="User One's secret vault combination is 9988.",
            uid="user_one",
            source="conversation",
        )

        # User Two asks about User One's vault
        result = process_reasoning_pipeline(
            question="What is the vault combination?",
            uid="user_two",
        )

        # Check that context received by Lyzr does NOT contain user_one's memory
        call_kwargs = mock_ask_lyzr.call_args[1]
        self.assertEqual(call_kwargs["context"], [])
        self.assertEqual(result["retrieved_memory_count"], 0)
        # Check notification target is strictly user_two
        mock_send_notif.assert_called_once_with(
            uid="user_two",
            message="No relevant info found.",
        )


if __name__ == "__main__":
    unittest.main()
