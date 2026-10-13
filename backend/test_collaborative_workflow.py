"""
Unit and integration tests for MEMORA Collaborative Multi-Agent Orchestration (Stage 2B.9).
Verifies:
1. Classification accuracy:
   - Declarative statements remain memory captures (False).
   - Memory/note commands remain excluded (False).
   - Simple single-focus questions continue to pass (True).
   - Compound utterance from Stage 2B.6 is recognized as an explicit request (True).
2. Combined query detector:
   - Distinguishes combined recall + planning requests from single-focus recall or planning requests.
3. lyzr_service direct agent invocation:
   - ask_lyzr allows custom agent_id parameter (e.g. Action Planner).
4. Sequential collaborative orchestration pipeline:
   - Qdrant memory retrieval -> MEMORA Reasoner -> MEMORA Action Planner -> final response.
   - Reasoner output is passed into Action Planner's context.
   - workers_invoked and execution_trace honestly reflect both workers in chronological order.
   - Partial failure handling: Action Planner failure is recorded honestly as failed, Reasoner answer preserved.
   - Ordinary single-focus queries continue using the Lyzr Manager route.
   - Background tasks, persistence isolation, and notification behavior remain intact.

All external calls (Lyzr API, Omi Notifications) are 100% mocked.
No live inference or notifications are triggered.
"""

import os
import sys
import json
import uuid
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app import (
    app,
    is_explicit_question,
    is_combined_recall_planning_query,
    process_reasoning_pipeline,
    init_qdrant_collection,
    store_memory,
    reset_processed_events,
    reset_latest_reasoning_result,
    get_reasoning_result_file_path,
)
import lyzr_service


class TestCollaborativeWorkflow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        reset_processed_events()
        reset_latest_reasoning_result()
        # Set up an isolated reasoning result file for each test
        self.temp_dir = tempfile.mkdtemp()
        self.isolated_file = os.path.join(self.temp_dir, f"test_reason_{uuid.uuid4().hex[:6]}.json")
        self.env_patcher = patch.dict(os.environ, {
            "MEMORA_REASONING_RESULT_FILE": self.isolated_file,
            "LYZR_API_KEY": "mock_lyzr_key_123",
            "LYZR_AGENT_ID": "6ac7c057b300b2daefd99218",
            "LYZR_ACTION_PLANNER_AGENT_ID": "6ac7eba918b1643ee32dad1d",
            "LYZR_MANAGER_AGENT_ID": "6ac7ec8f6f28ab116dc67d3b",
            "OMI_APP_ID": "mock_app_id",
            "OMI_APP_SECRET": "mock_secret",
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        reset_latest_reasoning_result()
        if os.path.exists(self.isolated_file):
            try:
                os.remove(self.isolated_file)
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # 1. Question Classification & Compound Request Detection
    # -------------------------------------------------------------------------
    def test_declarative_statements_remain_memory_captures(self):
        """Declarative statements must NOT be detected as explicit questions/requests."""
        statements = [
            "I studied DBMS today.",
            "Meeting with team went very well.",
            "The weather is nice outside.",
            "I have my MSF class tomorrow.",
            "Alex mentioned that the project deadline is next Friday.",
            "",
            "   ",
        ]
        for stmt in statements:
            with self.subTest(stmt=stmt):
                self.assertFalse(is_explicit_question(stmt), f"Expected False for declarative statement: '{stmt}'")

    def test_memory_storage_commands_remain_excluded(self):
        """Commands to store or remember information must NOT trigger the reasoning pipeline."""
        commands = [
            "Remember that my MSF class is tomorrow at 9 AM.",
            "Remember to pay the electricity bill.",
            "Note that the server is restarting.",
            "Don't forget to call Mom.",
            "dont forget that meeting is delayed",
            "Save this note for later.",
            "Store this information.",
            "Remind me to submit the assignment.",
            "Remind me that my passport expires next month.",
            "Keep in mind that John is traveling.",
        ]
        for cmd in commands:
            with self.subTest(cmd=cmd):
                self.assertFalse(is_explicit_question(cmd), f"Expected False for storage command: '{cmd}'")

    def test_simple_question_classifications_continue_to_pass(self):
        """Standard questions must continue to be recognized as explicit questions."""
        questions = [
            "What class do I have tomorrow?",
            "when is my MSF class",
            "What did I study yesterday?",
            "Do I have any reminders about the project?",
            "What did I say about Rahul?",
            "Where did I leave my keys?",
            "Tell me about the meeting on Monday",
            "Can you tell me what the password is?",
        ]
        for q in questions:
            with self.subTest(q=q):
                self.assertTrue(is_explicit_question(q), f"Expected True for question: '{q}'")

    def test_stage_2b6_compound_utterance_recognized_as_request(self):
        """The compound recall + planning utterance from Stage 2B.6 must be recognized as an explicit request."""
        compound_utterance = (
            "I have my MSF class tomorrow. Based on what you remember about it, "
            "tell me what I need to prepare and give me a short checklist."
        )
        self.assertTrue(
            is_explicit_question(compound_utterance),
            "Stage 2B.6 compound utterance must be recognized by is_explicit_question"
        )

    def test_additional_compound_utterances_recognized(self):
        """Various compound utterances with declarative clauses followed by requests must be recognized."""
        compound_utterances = [
            "I'm heading to my exam now. Tell me what I should review before entering.",
            "Tomorrow is our team sync. Based on your memory, give me a plan.",
            "I'm working on the deck. What do I need to prepare and give me a checklist?",
        ]
        for utterance in compound_utterances:
            with self.subTest(utterance=utterance):
                self.assertTrue(is_explicit_question(utterance))

    # -------------------------------------------------------------------------
    # 2. Combined Recall + Planning Intent Detection
    # -------------------------------------------------------------------------
    def test_combined_recall_planning_query_detection(self):
        """Identifies queries that require BOTH memory recall and action planning."""
        combined_queries = [
            "I have my MSF class tomorrow. Based on what you remember about it, tell me what I need to prepare and give me a short checklist.",
            "Based on what you recall about the meeting, give me a preparation plan.",
            "What did I note about the project, and give me a checklist to prepare?",
            "Recall what I said about the demo and prepare a checklist.",
        ]
        for q in combined_queries:
            with self.subTest(q=q):
                self.assertTrue(
                    is_combined_recall_planning_query(q),
                    f"Expected True for combined query: '{q}'"
                )

        single_focus_recall = [
            "What class do I have tomorrow?",
            "When is my MSF class?",
            "What did I study yesterday?",
            "Where did I park my car?",
        ]
        for q in single_focus_recall:
            with self.subTest(q=q):
                self.assertFalse(
                    is_combined_recall_planning_query(q),
                    f"Expected False for recall-only query: '{q}'"
                )

        single_focus_planning = [
            "What preparation steps should I plan for my class tomorrow?",
            "Give me a checklist for tomorrow.",
            "What should I prepare for my presentation?",
            "Give me an action plan.",
        ]
        for q in single_focus_planning:
            with self.subTest(q=q):
                self.assertFalse(
                    is_combined_recall_planning_query(q),
                    f"Expected False for planning-only query: '{q}'"
                )

    # -------------------------------------------------------------------------
    # 3. lyzr_service Direct Agent Invocation
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_ask_lyzr_with_custom_agent_id(self, mock_post):
        """ask_lyzr must support invoking an explicit agent_id (e.g. Action Planner)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Custom agent output"}
        mock_post.return_value = mock_resp

        action_planner_id = "6ac7eba918b1643ee32dad1d"
        result = lyzr_service.ask_lyzr(
            question="Prepare a checklist",
            context=["Context 1"],
            user_id="test_user",
            session_id="test_sess",
            agent_id=action_planner_id,
        )

        self.assertEqual(result["agent_id"], action_planner_id)
        self.assertEqual(result["answer"], "Custom agent output")
        # Ensure payload dispatched to Lyzr had the custom agent_id
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["agent_id"], action_planner_id)

    @patch("requests.post")
    def test_ask_lyzr_default_uses_configured_agent_id(self, mock_post):
        """ask_lyzr without agent_id parameter falls back to LYZR_AGENT_ID."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Default agent output"}
        mock_post.return_value = mock_resp

        result = lyzr_service.ask_lyzr(
            question="What is my note?",
            context=["Context note"],
            user_id="test_user",
            session_id="test_sess",
        )

        self.assertEqual(result["agent_id"], "6ac7c057b300b2daefd99218")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["agent_id"], "6ac7c057b300b2daefd99218")

    # -------------------------------------------------------------------------
    # 4. Sequential Collaborative Orchestration Pipeline
    # -------------------------------------------------------------------------
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_combined_query_executes_reasoner_then_action_planner(self, mock_noti, mock_ask_lyzr):
        """
        Combined query must execute:
        1. Memory retrieval from Qdrant
        2. MEMORA Reasoner (with retrieved memories)
        3. MEMORA Action Planner (with Reasoner's output in context)
        4. Synthesized final answer
        5. Omi push notification
        """
        mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}

        # Store test memory in Qdrant
        test_uid = f"user_collab_{uuid.uuid4().hex[:6]}"
        store_memory(
            text="MSF class is tomorrow at 9 AM. Bring laptop and notebook.",
            uid=test_uid,
            source="manual",
        )

        reasoner_id = "6ac7c057b300b2daefd99218"
        planner_id = "6ac7eba918b1643ee32dad1d"

        # Side effect for ask_lyzr depending on target agent_id
        def ask_lyzr_side_effect(**kwargs):
            target_agent = kwargs.get("agent_id")
            if target_agent == reasoner_id:
                return {
                    "answer": "Your MSF class is tomorrow at 9 AM. You need to bring your laptop and notebook.",
                    "session_id": kwargs.get("session_id"),
                    "agent_id": reasoner_id,
                    "user_id": kwargs.get("user_id"),
                }
            elif target_agent == planner_id:
                # Check that Reasoner's output was passed in context
                context = kwargs.get("context", "")
                self.assertIn("Your MSF class is tomorrow at 9 AM", str(context))
                return {
                    "answer": "1. Charge laptop\n2. Pack notebook and pen\n3. Set alarm for 7:30 AM",
                    "session_id": kwargs.get("session_id"),
                    "agent_id": planner_id,
                    "user_id": kwargs.get("user_id"),
                }
            raise ValueError(f"Unexpected agent_id: {target_agent}")

        mock_ask_lyzr.side_effect = ask_lyzr_side_effect

        question = (
            "I have my MSF class tomorrow. Based on what you remember about it, "
            "tell me what I need to prepare and give me a short checklist."
        )

        result = process_reasoning_pipeline(
            question=question,
            uid=test_uid,
            session_id=f"sess-{uuid.uuid4().hex[:6]}",
        )

        # 1. Pipeline status & honest orchestration mode
        self.assertEqual(result["processing_status"], "completed")
        self.assertEqual(result["orchestration_mode"], "deterministic_sequential")
        self.assertFalse(result["delegation_observed"], "Backend sequential orchestration must not be claimed as Lyzr Manager delegation")

        # 2. Both workers invoked in order with readable names and IDs
        self.assertEqual(len(result["workers_invoked"]), 2)
        # Reasoner
        self.assertEqual(result["workers_invoked"][0]["agent_id"], reasoner_id)
        self.assertEqual(result["workers_invoked"][0]["agent_name"], "MEMORA Reasoner")
        self.assertEqual(result["workers_invoked"][0]["worker_name"], "MEMORA Reasoner")
        self.assertEqual(result["workers_invoked"][0]["status"], "completed")
        # Action Planner
        self.assertEqual(result["workers_invoked"][1]["agent_id"], planner_id)
        self.assertEqual(result["workers_invoked"][1]["agent_name"], "MEMORA Action Planner")
        self.assertEqual(result["workers_invoked"][1]["worker_name"], "MEMORA Action Planner")
        self.assertEqual(result["workers_invoked"][1]["status"], "completed")

        # 3. Execution trace has readable display fields for frontend
        self.assertEqual(len(result["execution_trace"]), 4)
        # Step 1: Reasoner start
        s1 = result["execution_trace"][0]
        self.assertEqual(s1["event_type"], "worker_started")
        self.assertEqual(s1["agent"], "MEMORA Orchestrator")
        self.assertEqual(s1["action"], "invoke_worker")
        self.assertEqual(s1["target"], "MEMORA Reasoner")
        self.assertEqual(s1["agent_id"], reasoner_id)
        self.assertEqual(s1["worker_name"], "MEMORA Reasoner")
        self.assertIn("timestamp", s1)

        # Step 2: Reasoner completed
        s2 = result["execution_trace"][1]
        self.assertEqual(s2["event_type"], "worker_completed")
        self.assertEqual(s2["agent"], "MEMORA Reasoner")
        self.assertEqual(s2["action"], "completed")
        self.assertEqual(s2["status"], "completed")
        self.assertEqual(s2["agent_id"], reasoner_id)

        # Step 3: Planner start
        s3 = result["execution_trace"][2]
        self.assertEqual(s3["event_type"], "worker_started")
        self.assertEqual(s3["agent"], "MEMORA Orchestrator")
        self.assertEqual(s3["action"], "invoke_worker")
        self.assertEqual(s3["target"], "MEMORA Action Planner")
        self.assertEqual(s3["agent_id"], planner_id)

        # Step 4: Planner completed
        s4 = result["execution_trace"][3]
        self.assertEqual(s4["event_type"], "worker_completed")
        self.assertEqual(s4["agent"], "MEMORA Action Planner")
        self.assertEqual(s4["action"], "completed")
        self.assertEqual(s4["status"], "completed")
        self.assertEqual(s4["agent_id"], planner_id)

        # 4. Final synthesized answer contains findings from both
        self.assertIn("9 AM", result["manager_answer"])
        self.assertIn("Charge laptop", result["manager_answer"])

        # 5. Omi push notification was sent
        mock_noti.assert_called_once()
        noti_args, noti_kwargs = mock_noti.call_args
        self.assertEqual(noti_kwargs.get("uid"), test_uid)
        self.assertEqual(noti_kwargs.get("message"), result["manager_answer"])

    # -------------------------------------------------------------------------
    # 5. Action Planner Partial Failure Handling
    # -------------------------------------------------------------------------
    @patch("lyzr_service.ask_lyzr")
    @patch("omi_service.send_omi_notification")
    def test_action_planner_failure_preserves_reasoner_output_and_records_failure(self, mock_noti, mock_ask_lyzr):
        """
        If Action Planner fails, MEMORA must:
        - Record Action Planner status as 'failed' (never fabricate 'completed').
        - Retain and deliver Reasoner's valid answer to user.
        - Send notification with Reasoner's output.
        - Honestly report sequential orchestration without claiming Manager delegation.
        """
        mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}

        test_uid = f"user_collab_fail_{uuid.uuid4().hex[:6]}"
        store_memory(
            text="MSF class is tomorrow at 9 AM in Room 402.",
            uid=test_uid,
            source="manual",
        )

        reasoner_id = "6ac7c057b300b2daefd99218"
        planner_id = "6ac7eba918b1643ee32dad1d"

        def ask_lyzr_side_effect(**kwargs):
            target_agent = kwargs.get("agent_id")
            if target_agent == reasoner_id:
                return {
                    "answer": "Your MSF class is tomorrow at 9 AM in Room 402.",
                    "session_id": kwargs.get("session_id"),
                    "agent_id": reasoner_id,
                    "user_id": kwargs.get("user_id"),
                }
            elif target_agent == planner_id:
                raise RuntimeError("Lyzr Action Planner inference timed out")
            raise ValueError(f"Unexpected agent_id: {target_agent}")

        mock_ask_lyzr.side_effect = ask_lyzr_side_effect

        question = (
            "I have my MSF class tomorrow. Based on what you remember about it, "
            "tell me what I need to prepare and give me a short checklist."
        )

        result = process_reasoning_pipeline(
            question=question,
            uid=test_uid,
            session_id=f"sess-fail-{uuid.uuid4().hex[:6]}",
        )

        # 1. Processing completed (with graceful degradation)
        self.assertEqual(result["processing_status"], "completed")
        self.assertEqual(result["orchestration_mode"], "deterministic_sequential")
        self.assertFalse(result["delegation_observed"])

        # 2. Honest worker records
        self.assertEqual(len(result["workers_invoked"]), 2)
        self.assertEqual(result["workers_invoked"][0]["agent_name"], "MEMORA Reasoner")
        self.assertEqual(result["workers_invoked"][0]["status"], "completed")

        self.assertEqual(result["workers_invoked"][1]["agent_name"], "MEMORA Action Planner")
        self.assertEqual(result["workers_invoked"][1]["status"], "failed")

        # 3. Execution trace has worker_failed event with truthful display fields
        s4 = result["execution_trace"][3]
        self.assertEqual(s4["event_type"], "worker_failed")
        self.assertEqual(s4["agent"], "MEMORA Action Planner")
        self.assertEqual(s4["action"], "failed")
        self.assertEqual(s4["status"], "failed")
        self.assertIn("Lyzr Action Planner inference timed out", s4["error"])

        # 4. Reasoner answer is preserved in the manager answer
        self.assertIn("Room 402", result["manager_answer"])

        # 5. Notification was still sent with Reasoner's output
        mock_noti.assert_called_once()
        self.assertIn("Room 402", mock_noti.call_args[1]["message"])

    # -------------------------------------------------------------------------
    # 6. Ordinary Single-Focus Queries Continue to Use Manager Route
    # -------------------------------------------------------------------------
    @patch("lyzr_service.call_lyzr_manager")
    @patch("omi_service.send_omi_notification")
    def test_ordinary_single_focus_query_uses_manager_route(self, mock_noti, mock_manager):
        """Single-focus queries must continue to route to call_lyzr_manager, not the sequential chain."""
        mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}
        mock_manager.return_value = {
            "answer": "Your MSF class is tomorrow at 9 AM.",
            "session_id": "sess-mgr-001",
            "manager_agent_id": "6ac7ec8f6f28ab116dc67d3b",
            "user_id": "test_user",
            "telemetry": {
                "telemetry_status": "available",
                "delegation_observed": True,
                "workers_invoked": [{"worker_name": "MEMORA Reasoner", "agent_id": "6ac7c057b300b2daefd99218", "status": "completed"}],
                "execution_trace": [],
            }
        }

        test_uid = f"user_single_{uuid.uuid4().hex[:6]}"
        question = "What class do I have tomorrow?"

        result = process_reasoning_pipeline(
            question=question,
            uid=test_uid,
            session_id="sess-single-001",
        )

        # call_lyzr_manager must be called
        mock_manager.assert_called_once()
        self.assertEqual(result["orchestration_mode"], "lyzr_managed_agents")
        self.assertEqual(result["manager_answer"], "Your MSF class is tomorrow at 9 AM.")

    # -------------------------------------------------------------------------
    # 7. Webhook Integration for Compound Utterance
    # -------------------------------------------------------------------------
    @patch("app.process_reasoning_pipeline")
    def test_webhook_dispatches_compound_utterance_to_reasoning_pipeline(self, mock_pipeline):
        """When Omi webhook receives the Stage 2B.6 compound utterance, it triggers reasoning pipeline."""
        mock_pipeline.return_value = {
            "processing_status": "completed",
            "manager_answer": "Mock compound response",
        }

        test_uid = f"user_omi_compound_{uuid.uuid4().hex[:6]}"
        payload = {
            "id": f"conv-compound-{uuid.uuid4().hex[:6]}",
            "transcript_segments": [{
                "text": "I have my MSF class tomorrow. Based on what you remember about it, tell me what I need to prepare and give me a short checklist."
            }],
            "structured": {
                "overview": "User asking for class preparation checklist."
            }
        }

        response = self.client.post(f"/omi/conversation?uid={test_uid}", json=payload)
        self.assertEqual(response.status_code, 200)

        # FastAPI BackgroundTasks executes after response
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        self.assertEqual(call_kwargs["uid"], test_uid)
        self.assertIn("Based on what you remember", call_kwargs["question"])


if __name__ == "__main__":
    unittest.main()
