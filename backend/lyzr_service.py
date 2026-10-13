"""
Lyzr Agent Studio integration service for MEMORA.
Handles communication with deployed Lyzr agents (e.g. MEMORA Reasoner)
for reasoning over retrieved voice memories.
"""

import os
import uuid
import logging
from typing import Optional, List, Union, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

logger = logging.getLogger("memora-lyzr")

DEFAULT_LYZR_URL = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"


def get_lyzr_config() -> Dict[str, str]:
    """
    Validate and return Lyzr configuration from environment variables.
    Raises ValueError if required configurations are missing.
    """
    api_key = os.getenv("LYZR_API_KEY", "").strip()
    agent_id = os.getenv("LYZR_AGENT_ID", "").strip() or os.getenv("LYZR_MANAGER_AGENT_ID", "").strip()
    action_planner_agent_id = os.getenv("LYZR_ACTION_PLANNER_AGENT_ID", "6ac7eba918b1643ee32dad1d").strip()
    api_url = os.getenv("LYZR_API_URL", DEFAULT_LYZR_URL).strip() or DEFAULT_LYZR_URL

    if not api_key:
        raise ValueError("LYZR_API_KEY is not configured in environment variables.")
    if not agent_id:
        raise ValueError("LYZR_AGENT_ID is not configured in environment variables.")

    return {
        "api_key": api_key,
        "agent_id": agent_id,
        "action_planner_agent_id": action_planner_agent_id,
        "api_url": api_url,
    }


def get_lyzr_manager_config() -> Dict[str, str]:
    """
    Validate and return Lyzr Manager configuration from environment variables.
    Raises ValueError if required configurations are missing.
    """
    api_key = os.getenv("LYZR_API_KEY", "").strip()
    manager_agent_id = os.getenv("LYZR_MANAGER_AGENT_ID", "").strip() or os.getenv("LYZR_AGENT_ID", "").strip()
    api_url = os.getenv("LYZR_API_URL", DEFAULT_LYZR_URL).strip() or DEFAULT_LYZR_URL

    if not api_key:
        raise ValueError("LYZR_API_KEY is not configured in environment variables.")
    if not manager_agent_id:
        raise ValueError("LYZR_MANAGER_AGENT_ID is not configured in environment variables.")

    return {
        "api_key": api_key,
        "manager_agent_id": manager_agent_id,
        "api_url": api_url,
    }



def format_reasoning_prompt(question: str, context: Optional[Union[List[str], str]] = None) -> str:
    """
    Constructs the grounded reasoning prompt for Lyzr Reasoner:
    CONTEXT:
    <relevant memories>

    QUESTION:
    <user question>
    """
    if isinstance(context, list):
        if context:
            formatted_context = "\n".join(f"- {c.strip()}" for c in context if c and c.strip())
        else:
            formatted_context = "No relevant voice memories found."
    elif isinstance(context, str) and context.strip():
        formatted_context = context.strip()
    else:
        formatted_context = "No relevant voice memories found."

    clean_question = question.strip() if question else ""

    return f"CONTEXT:\n{formatted_context}\n\nQUESTION:\n{clean_question}"


def parse_lyzr_response(response_data: Any) -> str:
    """
    Defensively extracts the text answer from Lyzr's response payload.
    Supports standard Lyzr format: {"response": "..."}, {"message": "..."},
    nested objects, or fallback string representations.
    """
    if isinstance(response_data, dict):
        if "response" in response_data and isinstance(response_data["response"], str):
            return response_data["response"].strip()
        if "message" in response_data and isinstance(response_data["message"], str):
            return response_data["message"].strip()
        if "answer" in response_data and isinstance(response_data["answer"], str):
            return response_data["answer"].strip()
        if "output" in response_data and isinstance(response_data["output"], str):
            return response_data["output"].strip()
        # Check nested module_outputs or response dicts
        for key in ("response", "result", "data"):
            val = response_data.get(key)
            if isinstance(val, dict):
                for sub_key in ("text", "content", "response", "message"):
                    if isinstance(val.get(sub_key), str):
                        return val[sub_key].strip()
        # Fallback if dictionary has unknown keys
        return str(response_data)
    elif isinstance(response_data, str):
        return response_data.strip()
    return str(response_data)


def ask_lyzr(
    question: str,
    context: Optional[Union[List[str], str]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Sends question and retrieved memory context to the configured Lyzr Agent.
    Supports targeting an explicit agent_id (e.g. MEMORA Reasoner or MEMORA Action Planner).
    Returns structured answer dict without ever exposing secrets.
    """
    config = get_lyzr_config()

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    target_agent_id = (agent_id or config["agent_id"]).strip()
    effective_user_id = (user_id or os.getenv("LYZR_USER_ID", "default_user")).strip()
    effective_session_id = (
        session_id
        or os.getenv("LYZR_DEFAULT_SESSION_ID")
        or f"{target_agent_id}-{uuid.uuid4().hex[:8]}"
    ).strip()

    prompt_message = format_reasoning_prompt(question=question, context=context)

    payload = {
        "user_id": effective_user_id,
        "agent_id": target_agent_id,
        "session_id": effective_session_id,
        "message": prompt_message,
    }

    # Headers containing API key - NEVER log headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
    }

    logger.info(
        f"Dispatching reasoning prompt to Lyzr Agent [{target_agent_id}] (user='{effective_user_id}', "
        f"session='{effective_session_id}', context_items={len(context) if isinstance(context, list) else 1})"
    )

    try:
        response = requests.post(
            config["api_url"],
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout:
        logger.error("Lyzr API request timed out.")
        raise RuntimeError("Lyzr inference request timed out.")
    except requests.RequestException as e:
        logger.error(f"Lyzr network error: {type(e).__name__}")
        raise RuntimeError(f"Lyzr network communication error: {type(e).__name__}")

    if response.status_code != 200:
        logger.error(f"Lyzr API returned non-200 status code: {response.status_code}")
        raise RuntimeError(f"Lyzr API error: HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        data = {"response": response.text}

    answer = parse_lyzr_response(data)

    return {
        "answer": answer,
        "session_id": effective_session_id,
        "agent_id": target_agent_id,
        "user_id": effective_user_id,
    }


def call_lyzr_manager(
    question: str,
    context: Optional[Union[List[str], str]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Sends question and retrieved memory context to the configured Lyzr Manager Agent.
    The Manager Agent orchestrates configured worker agents (e.g. MEMORA Reasoner and MEMORA Action Planner)
    via Lyzr's managed_agents capability in Lyzr Agent Studio.
    Returns structured answer dict without ever exposing secrets.
    """
    config = get_lyzr_manager_config()

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    effective_user_id = (user_id or os.getenv("LYZR_USER_ID", "default_user")).strip()
    effective_session_id = (
        session_id
        or os.getenv("LYZR_DEFAULT_SESSION_ID")
        or f"{config['manager_agent_id']}-{uuid.uuid4().hex[:8]}"
    ).strip()

    prompt_message = format_reasoning_prompt(question=question, context=context)

    payload = {
        "user_id": effective_user_id,
        "agent_id": config["manager_agent_id"],
        "session_id": effective_session_id,
        "message": prompt_message,
    }

    # Headers containing API key - NEVER log headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
    }

    logger.info(
        f"Dispatching query to Lyzr Manager Agent [{config['manager_agent_id']}] (user='{effective_user_id}', "
        f"session='{effective_session_id}', context_items={len(context) if isinstance(context, list) else 1})"
    )

    # Start non-blocking telemetry listener before inference request
    collector = None
    try:
        from lyzr_telemetry import TelemetryCollector
        c = TelemetryCollector(
            session_id=effective_session_id,
            api_key=config["api_key"],
        )
        c.start()
        collector = c
    except Exception as tel_init_err:
        logger.warning(f"Telemetry collector initialization skipped: {tel_init_err}")

    telemetry_data = {
        "telemetry_status": "unavailable",
        "delegation_observed": False,
        "workers_invoked": [],
        "execution_trace": [],
    }

    try:
        response = requests.post(
            config["api_url"],
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout:
        if collector:
            collector.stop(wait_seconds=0.5)
        logger.error("Lyzr Manager API request timed out.")
        raise RuntimeError("Lyzr inference request timed out.")
    except requests.RequestException as e:
        if collector:
            collector.stop(wait_seconds=0.5)
        logger.error(f"Lyzr Manager network error: {type(e).__name__}")
        raise RuntimeError(f"Lyzr network communication error: {type(e).__name__}")

    # Stop telemetry listener and harvest trace frames
    if collector:
        try:
            telemetry_data = collector.stop(wait_seconds=2.0)
        except Exception as tel_stop_err:
            logger.warning(f"Failed to harvest telemetry: {tel_stop_err}")

    if response.status_code != 200:
        logger.error(f"Lyzr Manager API returned non-200 status code: {response.status_code}")
        raise RuntimeError(f"Lyzr API error: HTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        data = {"response": response.text}

    answer = parse_lyzr_response(data)

    return {
        "answer": answer,
        "session_id": effective_session_id,
        "manager_agent_id": config["manager_agent_id"],
        "user_id": effective_user_id,
        "raw_response": data,
        "telemetry": telemetry_data,
    }

