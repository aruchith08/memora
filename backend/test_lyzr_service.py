"""
Unit tests for Lyzr Agent Studio integration service (MEMORA Reasoner).
All HTTP calls are mocked with unittest.mock; no live API calls are made.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import requests

from lyzr_service import (
    ask_lyzr,
    format_reasoning_prompt,
    parse_lyzr_response,
    get_lyzr_config,
)


class TestLyzrService(unittest.TestCase):

    def setUp(self):
        self.mock_env = {
            "LYZR_API_KEY": "test-mock-key-12345",
            "LYZR_AGENT_ID": "mock-agent-xyz",
            "LYZR_API_URL": "https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
            "LYZR_USER_ID": "test_user@example.com",
        }

    # 1. Successful Lyzr response
    def test_successful_lyzr_response(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "response": "Your MSF class is scheduled for tomorrow morning.",
                    "module_outputs": {},
                }
                mock_post.return_value = mock_resp

                result = ask_lyzr(
                    question="When is my class?",
                    context=["MSF class is tomorrow morning."],
                    user_id="test_user@example.com",
                    session_id="session-001",
                )

                self.assertEqual(result["answer"], "Your MSF class is scheduled for tomorrow morning.")
                self.assertEqual(result["session_id"], "session-001")
                self.assertEqual(result["agent_id"], "mock-agent-xyz")

                # Verify request payload & headers
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(kwargs["headers"]["x-api-key"], "test-mock-key-12345")
                self.assertIn("CONTEXT:\n- MSF class is tomorrow morning.", kwargs["json"]["message"])
                self.assertIn("QUESTION:\nWhen is my class?", kwargs["json"]["message"])

    # 2. Lyzr non-2xx response
    def test_lyzr_non_2xx_response(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_resp.text = "Internal Server Error"
                mock_post.return_value = mock_resp

                with self.assertRaises(RuntimeError) as ctx:
                    ask_lyzr(
                        question="When is my class?",
                        context=["MSF class is tomorrow."],
                    )
                self.assertIn("HTTP 500", str(ctx.exception))
                # Ensure API key is NOT leaked in exception
                self.assertNotIn("test-mock-key-12345", str(ctx.exception))

    # 3. Timeout / network failure
    def test_timeout_network_failure(self):
        with patch.dict(os.environ, self.mock_env, clear=True):
            with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
                with self.assertRaises(RuntimeError) as ctx:
                    ask_lyzr(
                        question="When is my class?",
                        context=["MSF class is tomorrow."],
                    )
                self.assertIn("timed out", str(ctx.exception))

            with patch("requests.post", side_effect=requests.ConnectionError("Failed to resolve host")):
                with self.assertRaises(RuntimeError) as ctx:
                    ask_lyzr(
                        question="When is my class?",
                        context=["MSF class is tomorrow."],
                    )
                self.assertIn("network communication error", str(ctx.exception))

    # 4. Missing LYZR_API_KEY configuration
    def test_missing_api_key_configuration(self):
        incomplete_env = {
            "LYZR_API_KEY": "",
            "LYZR_AGENT_ID": "mock-agent-xyz",
        }
        with patch.dict(os.environ, incomplete_env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                ask_lyzr(question="When is my class?")
            self.assertIn("LYZR_API_KEY", str(ctx.exception))

    # 5. Missing LYZR_AGENT_ID configuration
    def test_missing_agent_id_configuration(self):
        incomplete_env = {
            "LYZR_API_KEY": "test-mock-key-12345",
            "LYZR_AGENT_ID": "",
        }
        with patch.dict(os.environ, incomplete_env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                ask_lyzr(question="When is my class?")
            self.assertIn("LYZR_AGENT_ID", str(ctx.exception))

    # 6. Defensive parsing of the response
    def test_defensive_parsing_of_response_shapes(self):
        # Format A: standard {"response": "..."}
        self.assertEqual(
            parse_lyzr_response({"response": "Answer A"}),
            "Answer A",
        )

        # Format B: {"message": "..."}
        self.assertEqual(
            parse_lyzr_response({"message": "Answer B"}),
            "Answer B",
        )

        # Format C: {"answer": "..."}
        self.assertEqual(
            parse_lyzr_response({"answer": "Answer C"}),
            "Answer C",
        )

        # Format D: nested {"data": {"response": "Nested answer"}}
        self.assertEqual(
            parse_lyzr_response({"data": {"response": "Nested answer"}}),
            "Nested answer",
        )

        # Format E: plain string
        self.assertEqual(
            parse_lyzr_response("Plain string answer"),
            "Plain string answer",
        )

    # 7. Prompt formatting verification
    def test_format_reasoning_prompt(self):
        prompt = format_reasoning_prompt(
            question="What did John say?",
            context=["John wants to reschedule the meeting to 3 PM.", "Meeting is on Zoom."],
        )
        self.assertIn("CONTEXT:\n- John wants to reschedule the meeting to 3 PM.\n- Meeting is on Zoom.", prompt)
        self.assertIn("QUESTION:\nWhat did John say?", prompt)

        # Empty context handling
        empty_context_prompt = format_reasoning_prompt(
            question="What did John say?",
            context=[],
        )
        self.assertIn("No relevant voice memories found.", empty_context_prompt)


if __name__ == "__main__":
    unittest.main()
