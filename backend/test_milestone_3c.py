"""
Milestone 3C Test Suite:
Explicit Question Detection -> Qdrant Retrieval -> Lyzr Reasoning Pipeline
Covers all 7 required scenarios + question detection verification.
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
    is_explicit_question,
    process_reasoning_pipeline,
    store_memory,
    retrieve_memories,
    init_qdrant_collection,
)


class TestMilestone3C(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    # Question detector unit tests
    def test_question_detection_logic(self):
        # Explicit questions
        self.assertTrue(is_explicit_question("What class do I have tomorrow?"))
        self.assertTrue(is_explicit_question("when is my MSF class"))
        self.assertTrue(is_explicit_question("What did I study yesterday?"))
        self.assertTrue(is_explicit_question("Do I have any reminders about the project?"))
        self.assertTrue(is_explicit_question("What did I say about Rahul?"))
        self.assertTrue(is_explicit_question("Where did I leave my keys?"))
        self.assertTrue(is_explicit_question("Tell me about the meeting on Monday"))
        self.assertTrue(is_explicit_question("Can you tell me what the password is?"))

        # Memory commands (Explicitly NOT questions)
        self.assertFalse(is_explicit_question("Remember that my MSF class is tomorrow at 9 AM."))
        self.assertFalse(is_explicit_question("Remember to pay the electricity bill."))
        self.assertFalse(is_explicit_question("Note that the server is restarting."))
        self.assertFalse(is_explicit_question("Don't forget to call Mom."))

        # Normal statements
        self.assertFalse(is_explicit_question("I studied DBMS today."))
        self.assertFalse(is_explicit_question("Meeting with team went very well."))
        self.assertFalse(is_explicit_question("The weather is nice outside."))
        self.assertFalse(is_explicit_question(""))

    # 1. Normal statement: stored as memory, Lyzr NOT called
    @patch("lyzr_service.ask_lyzr")
    def test_1_normal_statement_does_not_call_lyzr(self, mock_ask_lyzr):
        payload = {
            "transcript_segments": [{"text": "I studied DBMS and operating systems today."}],
            "structured": {"overview": "Study log for DBMS and OS."}
        }
        response = self.client.post("/omi/conversation?uid=user_statement_test", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        # Lyzr must NOT be called for normal statements
        mock_ask_lyzr.assert_not_called()

    # 2. Explicit question: question detected, Qdrant retrieval called, Lyzr called with context
    @patch("lyzr_service.ask_lyzr")
    def test_2_explicit_question_triggers_pipeline(self, mock_ask_lyzr):
        test_uid = f"user_q_test_{uuid.uuid4().hex[:8]}"
        mock_ask_lyzr.return_value = {
            "answer": "You studied DBMS and operating systems today.",
            "session_id": "sess-3c-002",
            "agent_id": "test-agent",
            "user_id": test_uid,
        }

        # Store previous memory
        store_memory(
            text="I studied DBMS and operating systems today.",
            uid=test_uid,
            source="conversation",
        )

        payload = {
            "transcript_segments": [{"text": "What did I study today?"}],
            "structured": {"overview": "User asked what they studied today."}
        }

        response = self.client.post(f"/omi/conversation?uid={test_uid}&session_id=sess-3c-002", json=payload)
        self.assertEqual(response.status_code, 200)

        # In TestClient, BackgroundTasks execute before response returns
        # Verify ask_lyzr was called with the question
        mock_ask_lyzr.assert_called_once()
        call_kwargs = mock_ask_lyzr.call_args[1]
        self.assertIn("What did I study today?", call_kwargs["question"])
        self.assertEqual(call_kwargs["user_id"], test_uid)
        self.assertTrue(len(call_kwargs["context"]) > 0)

    # 3. Question with relevant previous memory: Lyzr receives previous memory as context
    @patch("lyzr_service.ask_lyzr")
    def test_3_question_with_relevant_previous_memory(self, mock_ask_lyzr):
        mock_ask_lyzr.return_value = {
            "answer": "Your MSF class is tomorrow at 9 AM.",
            "session_id": "sess-msf-001",
            "agent_id": "test-agent",
            "user_id": "user_msf_test",
        }

        # Seed previous memory
        store_memory(
            text="My MSF class is scheduled for tomorrow at 9 AM in room 402.",
            uid="user_msf_test",
            source="conversation",
        )

        result = process_reasoning_pipeline(
            question="What class do I have tomorrow?",
            uid="user_msf_test",
            session_id="sess-msf-001",
        )

        self.assertEqual(result["processing_status"], "completed")
        self.assertTrue(result["retrieved_memory_count"] > 0)
        self.assertIn("Your MSF class is tomorrow", result["lyzr_answer"])

        # Check call arguments
        call_kwargs = mock_ask_lyzr.call_args[1]
        context_str = " ".join(call_kwargs["context"])
        self.assertIn("MSF class", context_str)

    # 4. Question with no relevant memory: Lyzr receives empty context
    @patch("lyzr_service.ask_lyzr")
    def test_4_question_with_no_relevant_memory(self, mock_ask_lyzr):
        mock_ask_lyzr.return_value = {
            "answer": "I do not have enough information in the provided context to answer that.",
            "session_id": "sess-empty-001",
            "agent_id": "test-agent",
            "user_id": "user_no_memory",
        }

        # Query for a brand-new user with zero memories
        result = process_reasoning_pipeline(
            question="Where did I hide the treasure chest?",
            uid="user_no_memory_at_all_999",
            session_id="sess-empty-001",
        )

        self.assertEqual(result["processing_status"], "completed")
        self.assertEqual(result["retrieved_memory_count"], 0)
        self.assertEqual(result["retrieved_memory_ids"], [])

        call_kwargs = mock_ask_lyzr.call_args[1]
        self.assertEqual(call_kwargs["context"], [])

    # 5. UID isolation: user A's memory is never provided to user B
    @patch("lyzr_service.ask_lyzr")
    def test_5_uid_isolation_in_reasoning(self, mock_ask_lyzr):
        mock_ask_lyzr.return_value = {
            "answer": "No information.",
            "session_id": "sess-iso",
            "agent_id": "test-agent",
            "user_id": "user_bob",
        }

        # User Alice has secret
        store_memory(
            text="Alice's top-secret project is Project Starlight.",
            uid="user_alice",
            source="conversation",
        )

        # User Bob queries about Alice's secret
        result = process_reasoning_pipeline(
            question="What is Project Starlight?",
            uid="user_bob",
            session_id="sess-iso",
        )

        # Bob must get 0 memories from Alice
        self.assertEqual(result["retrieved_memory_count"], 0)
        call_kwargs = mock_ask_lyzr.call_args[1]
        self.assertEqual(call_kwargs["context"], [])

    # 6. Self-retrieval protection: current question text is not in its own context
    @patch("lyzr_service.ask_lyzr")
    def test_6_self_retrieval_protection(self, mock_ask_lyzr):
        test_uid = f"user_self_test_{uuid.uuid4().hex[:8]}"
        mock_ask_lyzr.return_value = {
            "answer": "Exam is on Tuesday.",
            "session_id": "sess-self-test",
            "agent_id": "test-agent",
            "user_id": test_uid,
        }

        # Seed an actual past memory
        store_memory(
            text="The physics exam was moved to Tuesday at 2 PM.",
            uid=test_uid,
            source="conversation",
        )

        # Process question with store_question_as_memory=True
        question_text = "When is the physics exam?"
        result = process_reasoning_pipeline(
            question=question_text,
            uid=test_uid,
            session_id="sess-self-test",
            store_question_as_memory=True,
        )

        # Ensure question_text is not inside its own retrieved context
        call_kwargs = mock_ask_lyzr.call_args[1]
        for ctx_item in call_kwargs["context"]:
            self.assertNotEqual(ctx_item.strip().lower(), question_text.strip().lower())

    # 7. Lyzr failure handling: webhook stays 200, failure observable, no secret leak
    @patch("lyzr_service.ask_lyzr", side_effect=RuntimeError("Lyzr API error: HTTP 500"))
    def test_7_lyzr_failure_gracefully_handled(self, mock_ask_lyzr):
        payload = {
            "transcript_segments": [{"text": "What time is my flight?"}],
            "structured": {"overview": "User asked what time flight is."}
        }

        # Webhook must return 200 OK immediately
        response = self.client.post("/omi/conversation?uid=user_err_test", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

        # Check observable result endpoint
        obs_res = self.client.get("/reason/latest")
        self.assertEqual(obs_res.status_code, 200)
        obs_data = obs_res.json()
        self.assertEqual(obs_data["processing_status"], "error")
        self.assertIn("HTTP 500", obs_data["error"])
        # Ensure API key is not leaked in error
        self.assertNotIn("sk-default", str(obs_data))


if __name__ == "__main__":
    unittest.main()
