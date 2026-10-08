"""
Test suite for Lyzr multi-agent telemetry collection and sanitization.
Covers:
A. Telemetry event normalization
B. Manager worker-start detection
C. Worker completion detection
D. Manager completion detection
E. Unknown agent tool IDs ignored safely
F. Raw thinking_log is never persisted
G. Telemetry failure does not fail Manager inference
H. Manager inference failure is handled normally
I. /reason/latest exposes sanitized execution_trace
J. delegation_observed is true only when worker telemetry is actually observed
"""

import os
import sys
import uuid
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
    reset_processed_events,
)
from lyzr_telemetry import (
    normalize_telemetry_event,
    TelemetryCollector,
    KNOWN_WORKERS,
)
from lyzr_service import call_lyzr_manager


class TestLyzrTelemetry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_qdrant_collection()
        cls.client = TestClient(app)

    def setUp(self):
        reset_processed_events()
        self.mock_env = {
            "LYZR_API_KEY": "mock-lyzr-key-12345",
            "LYZR_AGENT_ID": "6ac7c057b300b2daefd99218",
            "LYZR_MANAGER_AGENT_ID": "6ac7ec8f6f28ab116dc67d3b",
            "LYZR_USER_ID": "test_user",
            "OMI_APP_ID": "mock-omi-app-id",
            "OMI_APP_SECRET": "mock-omi-secret-key",
        }

    # A. Telemetry event normalization
    def test_a_telemetry_event_normalization(self):
        # Manager process start
        mgr_ev = {
            "event_type": "agent_process_start",
            "agent_name": "MEMORA Manager",
            "timestamp": "2026-10-09T01:00:00Z",
        }
        norm = normalize_telemetry_event(mgr_ev)
        self.assertEqual(norm["event_type"], "manager_started")
        self.assertEqual(norm["agent_name"], "MEMORA Manager")

        # Process complete
        comp_ev = {
            "event_type": "process_complete",
            "agent_name": "MEMORA Manager",
            "timestamp": "2026-10-09T01:00:05Z",
        }
        norm_comp = normalize_telemetry_event(comp_ev)
        self.assertEqual(norm_comp["event_type"], "manager_completed")

    # B. Manager worker-start detection (both tool_called and agent_process_start)
    def test_b_worker_start_detection(self):
        # MEMORA Reasoner via tool_called
        tool_call_ev = {
            "event_type": "tool_called",
            "tool_name": "agent_tool_6ac7c057b300b2daefd99218",
            "agent_name": "MEMORA Manager",
            "timestamp": "2026-10-09T01:00:01Z",
        }
        norm = normalize_telemetry_event(tool_call_ev)
        self.assertEqual(norm["event_type"], "worker_started")
        self.assertEqual(norm["agent_name"], "MEMORA Reasoner")
        self.assertEqual(norm["agent_id"], "6ac7c057b300b2daefd99218")

        # MEMORA Action Planner via agent_process_start
        agent_start_ev = {
            "event_type": "agent_process_start",
            "agent_name": "MEMORA Action Planner",
            "timestamp": "2026-10-09T01:00:02Z",
        }
        norm2 = normalize_telemetry_event(agent_start_ev)
        self.assertEqual(norm2["event_type"], "worker_started")
        self.assertEqual(norm2["agent_name"], "MEMORA Action Planner")
        self.assertEqual(norm2["agent_id"], "6ac7eba918b1643ee32dad1d")

    # C. Worker completion detection
    def test_c_worker_completion_detection(self):
        # End via agent_process_end
        end_ev = {
            "event_type": "agent_process_end",
            "agent_name": "MEMORA Reasoner",
            "timestamp": "2026-10-09T01:00:03Z",
        }
        norm = normalize_telemetry_event(end_ev)
        self.assertEqual(norm["event_type"], "worker_completed")
        self.assertEqual(norm["agent_name"], "MEMORA Reasoner")

        # End via tool_output
        out_ev = {
            "event_type": "tool_output",
            "tool_name": "agent_tool_6ac7eba918b1643ee32dad1d",
            "timestamp": "2026-10-09T01:00:04Z",
        }
        norm2 = normalize_telemetry_event(out_ev)
        self.assertEqual(norm2["event_type"], "worker_completed")
        self.assertEqual(norm2["agent_name"], "MEMORA Action Planner")

    # D. Manager completion detection
    def test_d_manager_completion_detection(self):
        end_ev = {
            "event_type": "agent_process_end",
            "agent_name": "MEMORA Manager",
            "timestamp": "2026-10-09T01:00:06Z",
        }
        norm = normalize_telemetry_event(end_ev)
        self.assertEqual(norm["event_type"], "workflow_completed")
        self.assertEqual(norm["agent_name"], "MEMORA Manager")

    # E. Unknown agent tool IDs ignored safely
    def test_e_unknown_agent_tool_ignored(self):
        unk_ev = {
            "event_type": "tool_called",
            "tool_name": "agent_tool_unknown_id_9999",
            "agent_name": "MEMORA Manager",
        }
        norm = normalize_telemetry_event(unk_ev)
        self.assertIsNone(norm)

    # F. Raw thinking_log and llm_generation are never persisted
    def test_f_raw_thinking_log_and_generation_filtered(self):
        think_ev = {
            "event_type": "thinking_log",
            "thinking": "Secret user data I am thinking about right now...",
            "agent_name": "MEMORA Manager",
        }
        norm_think = normalize_telemetry_event(think_ev)
        self.assertIsNone(norm_think)

        gen_ev = {
            "event_type": "llm_generation",
            "content": "Raw generation text with private information",
        }
        norm_gen = normalize_telemetry_event(gen_ev)
        self.assertIsNone(norm_gen)

    # G. Telemetry failure does not fail Manager inference
    def test_g_telemetry_failure_does_not_fail_inference(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            # Simulate broken telemetry WebSocket
            with patch("lyzr_telemetry.TelemetryCollector.start", side_effect=Exception("WS connection refused")):
                with patch("requests.post") as mock_post:
                    mock_resp = MagicMock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = {"response": "Meeting is at 10 AM."}
                    mock_post.return_value = mock_resp

                    res = call_lyzr_manager(
                        question="When is the meeting?",
                        context=["Meeting at 10 AM."],
                    )

                    # Inference still succeeded
                    self.assertEqual(res["answer"], "Meeting is at 10 AM.")
                    self.assertIn("telemetry", res)
                    self.assertFalse(res["telemetry"]["delegation_observed"])
                    self.assertEqual(res["telemetry"]["telemetry_status"], "unavailable")

    # H. Manager inference failure is handled normally
    def test_h_manager_inference_failure_handled_normally(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post", side_effect=requests.Timeout("Inference timed out")):
                with self.assertRaises(RuntimeError) as ctx:
                    call_lyzr_manager(question="When is the meeting?")
                self.assertIn("timed out", str(ctx.exception))

    # I. /reason/latest exposes sanitized execution_trace
    def test_i_reason_latest_exposes_sanitized_trace(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            test_uid = f"user_telemetry_{uuid.uuid4().hex[:6]}"
            conv_id = f"conv-tel-{uuid.uuid4().hex[:6]}"

            mock_telemetry = {
                "telemetry_status": "collected",
                "delegation_observed": True,
                "workers_invoked": [
                    {
                        "agent_id": "6ac7c057b300b2daefd99218",
                        "agent_name": "MEMORA Reasoner",
                        "status": "completed",
                    },
                    {
                        "agent_id": "6ac7eba918b1643ee32dad1d",
                        "agent_name": "MEMORA Action Planner",
                        "status": "completed",
                    },
                ],
                "execution_trace": [
                    {"event_type": "manager_started", "timestamp": "2026-10-09T01:00:00Z"},
                    {"event_type": "worker_started", "agent_name": "MEMORA Reasoner", "agent_id": "6ac7c057b300b2daefd99218", "timestamp": "2026-10-09T01:00:01Z"},
                    {"event_type": "worker_started", "agent_name": "MEMORA Action Planner", "agent_id": "6ac7eba918b1643ee32dad1d", "timestamp": "2026-10-09T01:00:02Z"},
                    {"event_type": "worker_completed", "agent_name": "MEMORA Reasoner", "agent_id": "6ac7c057b300b2daefd99218", "timestamp": "2026-10-09T01:00:03Z"},
                    {"event_type": "worker_completed", "agent_name": "MEMORA Action Planner", "agent_id": "6ac7eba918b1643ee32dad1d", "timestamp": "2026-10-09T01:00:04Z"},
                    {"event_type": "manager_completed", "timestamp": "2026-10-09T01:00:05Z"},
                    {"event_type": "workflow_completed", "timestamp": "2026-10-09T01:00:06Z"},
                ],
            }

            with patch("lyzr_service.call_lyzr_manager") as mock_manager, \
                 patch("omi_service.send_omi_notification") as mock_noti:

                mock_manager.return_value = {
                    "answer": "Your demo is tomorrow at 10 AM. Action: prepare the slides.",
                    "session_id": conv_id,
                    "manager_agent_id": "6ac7ec8f6f28ab116dc67d3b",
                    "user_id": test_uid,
                    "telemetry": mock_telemetry,
                }
                mock_noti.return_value = {"status": "sent", "status_code": 200, "error": None}

                payload = {
                    "id": conv_id,
                    "transcript_segments": [{"text": "When is my demo meeting and what should I prepare?"}],
                    "structured": {"overview": "User asked about demo meeting."}
                }

                resp = self.client.post(f"/omi/conversation?uid={test_uid}", json=payload)
                self.assertEqual(resp.status_code, 200)

                obs_resp = self.client.get("/reason/latest")
                self.assertEqual(obs_resp.status_code, 200)
                obs_data = obs_resp.json()

                self.assertTrue(obs_data["delegation_observed"])
                self.assertEqual(obs_data["telemetry_status"], "collected")
                self.assertEqual(len(obs_data["workers_invoked"]), 2)
                self.assertEqual(obs_data["workers_invoked"][0]["agent_name"], "MEMORA Reasoner")
                self.assertEqual(obs_data["workers_invoked"][1]["agent_name"], "MEMORA Action Planner")
                self.assertEqual(len(obs_data["execution_trace"]), 7)

    # J. delegation_observed is true only when worker telemetry is actually observed
    def test_j_delegation_observed_requires_worker_telemetry(self):
        # Case 1: Telemetry with only manager events (no workers)
        collector = TelemetryCollector(session_id="test_no_workers")
        collector._raw_events = [
            {"event_type": "agent_process_start", "agent_name": "MEMORA Manager"},
            {"event_type": "process_complete", "agent_name": "MEMORA Manager"},
        ]
        result = collector._process_telemetry()
        self.assertFalse(result["delegation_observed"])
        self.assertEqual(len(result["workers_invoked"]), 0)

        # Case 2: Telemetry with worker event
        collector._raw_events.append({
            "event_type": "tool_called",
            "tool_name": "agent_tool_6ac7c057b300b2daefd99218",
            "agent_name": "MEMORA Manager",
        })
        result2 = collector._process_telemetry()
        self.assertTrue(result2["delegation_observed"])
        self.assertEqual(len(result2["workers_invoked"]), 1)


if __name__ == "__main__":
    unittest.main()
