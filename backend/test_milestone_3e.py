"""
Milestone 3E Test Suite:
Lyzr Multi-Agent Workflow: Connect Lyzr Manager to MEMORA Pipeline.
Verifies Manager configuration, prompt formatting, Lyzr Agent Studio inference,
multi-agent observability, Omi notification dispatch, and safety constraints.
"""

import os
import sys
import unittest
import uuid
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
    process_reasoning_pipeline,
    store_memory,
    retrieve_memories,
    init_qdrant_collection,
    reset_processed_events,
)
from lyzr_service import (
    get_lyzr_manager_config,
    call_lyzr_manager,
    format_reasoning_prompt,
)


class TestMilestone3E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        reset_processed_events()
        self.mock_env = {
            "LYZR_API_KEY": "mock-lyzr-secret-key-12345",
            "LYZR_AGENT_ID": "6ac7c057b300b2daefd99218",
            "LYZR_MANAGER_AGENT_ID": "6ac7ec8f6f28ab116dc67d3b",
            "LYZR_USER_ID": "test_user",
            "OMI_APP_ID": "mock-omi-app-id",
            "OMI_APP_SECRET": "mock-omi-secret-key",
        }

    # 1. Config validation tests
    def test_1_manager_config_validation(self):
        # Valid config
        with patch.dict(os.environ, self.mock_env, clear=True):
            config = get_lyzr_manager_config()
            self.assertEqual(config["api_key"], "mock-lyzr-secret-key-12345")
            self.assertEqual(config["manager_agent_id"], "6ac7ec8f6f28ab116dc67d3b")
            self.assertIn("https://agent-prod.studio.lyzr.ai", config["api_url"])

        # Missing API Key
        with patch.dict(os.environ, {"LYZR_MANAGER_AGENT_ID": "6ac7ec8f6f28ab116dc67d3b"}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                get_lyzr_manager_config()
            self.assertIn("LYZR_API_KEY", str(ctx.exception))

        # Missing Manager Agent ID
        with patch.dict(os.environ, {"LYZR_API_KEY": "some-key"}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                get_lyzr_manager_config()
            self.assertIn("LYZR_MANAGER_AGENT_ID", str(ctx.exception))

    # 2. Prompt formatting for Manager
    def test_2_manager_prompt_formatting(self):
        prompt = format_reasoning_prompt(
            question="What is the secret code?",
            context=["The secret code is Blue-7429.", "The test starts at 10 AM."],
        )
        self.assertIn("CONTEXT:", prompt)
        self.assertIn("- The secret code is Blue-7429.", prompt)
        self.assertIn("- The test starts at 10 AM.", prompt)
        self.assertIn("QUESTION:\nWhat is the secret code?", prompt)

    # 3. call_lyzr_manager calls LYZR_MANAGER_AGENT_ID (not LYZR_AGENT_ID)
    def test_3_call_lyzr_manager_targets_manager_id(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "response": "The secret code is Blue-7429. Next action: memorize it."
                }
                mock_post.return_value = mock_resp

                res = call_lyzr_manager(
                    question="What is the secret code?",
                    context=["The secret code is Blue-7429."],
                    user_id="user_test_3e",
                    session_id="session_test_3e",
                )

                self.assertEqual(res["answer"], "The secret code is Blue-7429. Next action: memorize it.")
                self.assertEqual(res["manager_agent_id"], "6ac7ec8f6f28ab116dc67d3b")
                self.assertEqual(res["session_id"], "session_test_3e")
                self.assertEqual(res["user_id"], "user_test_3e")

                # Verify payload agent_id is strictly the Manager Agent ID
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                payload = kwargs["json"]
                self.assertEqual(payload["agent_id"], "6ac7ec8f6f28ab116dc67d3b")
                self.assertNotEqual(payload["agent_id"], "6ac7c057b300b2daefd99218")
                self.assertEqual(kwargs["headers"]["x-api-key"], "mock-lyzr-secret-key-12345")

    # 4. Error handling in call_lyzr_manager
    def test_4_call_lyzr_manager_error_handling(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            # Empty question validation
            with self.assertRaises(ValueError):
                call_lyzr_manager(question="")

            # HTTP 500 error from Lyzr
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_post.return_value = mock_resp
                with self.assertRaises(RuntimeError) as ctx:
                    call_lyzr_manager(question="Where is my meeting?")
                self.assertIn("HTTP 500", str(ctx.exception))

    # 5. process_reasoning_pipeline executes Qdrant -> Lyzr Manager -> Omi notification
    def test_5_pipeline_full_execution_observability(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            test_uid = f"user_3e_pipeline_{uuid.uuid4().hex[:6]}"
            # Store memory in Qdrant
            store_memory(
                text="The project presentation is scheduled for Friday at 3 PM with Alice.",
                uid=test_uid,
                source="conversation",
            )

            with patch("lyzr_service.call_lyzr_manager") as mock_manager, \
                 patch("omi_service.send_omi_notification") as mock_noti:

                mock_manager.return_value = {
                    "answer": "Your presentation is on Friday at 3 PM with Alice. Action: Review the slide deck.",
                    "session_id": "sess-3e-pipe",
                    "manager_agent_id": "6ac7ec8f6f28ab116dc67d3b",
                    "user_id": test_uid,
                }
                mock_noti.return_value = {
                    "status": "sent",
                    "status_code": 200,
                    "error": None,
                }

                result = process_reasoning_pipeline(
                    question="When is my presentation scheduled?",
                    uid=test_uid,
                    session_id="sess-3e-pipe",
                    store_question_as_memory=True,
                )

                # Verify pipeline results and multi-agent observability
                self.assertEqual(result["processing_status"], "completed")
                self.assertEqual(result["manager_agent_id"], "6ac7ec8f6f28ab116dc67d3b")
                self.assertEqual(result["orchestration_mode"], "lyzr_managed_agents")
                self.assertFalse(result["delegation_observed"])
                self.assertEqual(result["manager_answer"], "Your presentation is on Friday at 3 PM with Alice. Action: Review the slide deck.")
                self.assertEqual(result["lyzr_answer"], result["manager_answer"])
                self.assertEqual(result["notification_status"], "sent")
                self.assertEqual(result["retrieved_memory_count"], 1)

                # Verify call_lyzr_manager received memory context
                mock_manager.assert_called_once()
                call_kwargs = mock_manager.call_args[1]
                self.assertEqual(call_kwargs["question"], "When is my presentation scheduled?")
                self.assertEqual(call_kwargs["user_id"], test_uid)
                self.assertTrue(len(call_kwargs["context"]) > 0)
                self.assertIn("Friday at 3 PM", call_kwargs["context"][0])

                # Verify Omi notification received synthesized Manager answer
                mock_noti.assert_called_once_with(
                    uid=test_uid,
                    message="Your presentation is on Friday at 3 PM with Alice. Action: Review the slide deck.",
                )

    # 6. Verify Lyzr Manager answer is NOT persisted into Qdrant
    def test_6_manager_answer_never_stored_in_qdrant(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            test_uid = f"user_3e_qdrant_check_{uuid.uuid4().hex[:6]}"
            manager_synth_text = "SYNTHESIZED_ANSWER_SHOULD_NEVER_ENTER_QDRANT_STORAGE"

            with patch("lyzr_service.call_lyzr_manager") as mock_manager, \
                 patch("omi_service.send_omi_notification"):

                mock_manager.return_value = {
                    "answer": manager_synth_text,
                    "session_id": "sess-3e-safe",
                    "manager_agent_id": "6ac7ec8f6f28ab116dc67d3b",
                    "user_id": test_uid,
                }

                process_reasoning_pipeline(
                    question="What is the milestone deadline?",
                    uid=test_uid,
                    session_id="sess-3e-safe",
                    store_question_as_memory=True,
                )

                # Query Qdrant for the synthesized text
                memories = retrieve_memories(question=manager_synth_text, uid=test_uid, limit=5)
                for mem in memories:
                    self.assertNotEqual(mem.get("text"), manager_synth_text)

    # 7. End-to-end webhook execution via TestClient and /reason/latest endpoint
    def test_7_webhook_e2e_and_reason_latest(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            test_uid = f"user_3e_webhook_{uuid.uuid4().hex[:6]}"
            conv_id = f"conv-3e-{uuid.uuid4().hex[:6]}"
            store_memory(
                text="The flight to San Francisco is departing at 6:45 AM on Terminal 2.",
                uid=test_uid,
                source="conversation",
            )

            with patch("lyzr_service.call_lyzr_manager") as mock_manager, \
                 patch("omi_service.send_omi_notification") as mock_noti:

                mock_manager.return_value = {
                    "answer": "Your flight departs at 6:45 AM from Terminal 2. Recommended action: Arrive by 4:45 AM.",
                    "session_id": conv_id,
                    "manager_agent_id": "6ac7ec8f6f28ab116dc67d3b",
                    "user_id": test_uid,
                }
                mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}

                payload = {
                    "id": conv_id,
                    "transcript_segments": [{"text": "What time does my flight depart?"}],
                    "structured": {"overview": "User asked about flight departure time."}
                }

                # Post to Omi conversation webhook
                response = self.client.post(f"/omi/conversation?uid={test_uid}", json=payload)
                self.assertEqual(response.status_code, 200)

                # Check /reason/latest endpoint
                obs_resp = self.client.get("/reason/latest")
                self.assertEqual(obs_resp.status_code, 200)
                obs_data = obs_resp.json()

                self.assertEqual(obs_data["uid"], test_uid)
                self.assertEqual(obs_data["manager_agent_id"], "6ac7ec8f6f28ab116dc67d3b")
                self.assertEqual(obs_data["orchestration_mode"], "lyzr_managed_agents")
                self.assertFalse(obs_data["delegation_observed"])
                self.assertEqual(obs_data["manager_answer"], "Your flight departs at 6:45 AM from Terminal 2. Recommended action: Arrive by 4:45 AM.")
                self.assertEqual(obs_data["lyzr_answer"], obs_data["manager_answer"])
                self.assertEqual(obs_data["notification_status"], "sent")
                self.assertEqual(obs_data["processing_status"], "completed")

    # 8. Normal statement does NOT invoke Lyzr Manager
    def test_8_normal_statement_does_not_invoke_manager(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("lyzr_service.call_lyzr_manager") as mock_manager:
                payload = {
                    "id": "conv-3e-normal",
                    "transcript_segments": [{"text": "I had lunch with Sarah and we discussed the budget."}],
                    "structured": {"overview": "Lunch conversation about budget."}
                }
                response = self.client.post("/omi/conversation?uid=user_normal_3e", json=payload)
                self.assertEqual(response.status_code, 200)
                mock_manager.assert_not_called()


if __name__ == "__main__":
    unittest.main()
