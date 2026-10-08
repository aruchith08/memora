"""
Lyzr Multi-Agent Telemetry Ingestion Service for MEMORA.
Connects non-blockingly to Lyzr's telemetry WebSocket:
  wss://metrics.studio.lyzr.ai/ws/{session_id}
Collects real-time execution frames, normalizes multi-agent workflow events,
sanitizes sensitive data, and guarantees graceful degradation if telemetry fails.
"""

import os
import json
import time
import logging
import threading
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import websockets
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

logger = logging.getLogger("memora-telemetry")

DEFAULT_WS_URL_TEMPLATE = "wss://metrics.studio.lyzr.ai/ws/{session_id}"

# Verified worker agent mapping
KNOWN_WORKERS = {
    "6ac7c057b300b2daefd99218": "MEMORA Reasoner",
    "6ac7eba918b1643ee32dad1d": "MEMORA Action Planner",
}

# Reverse mapping for agent_name resolution
NAME_TO_ID = {
    "MEMORA Reasoner": "6ac7c057b300b2daefd99218",
    "MEMORA Action Planner": "6ac7eba918b1643ee32dad1d",
}


def normalize_telemetry_event(raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Sanitizes and maps raw Lyzr telemetry event frames into normalized workflow events.
    Strictly filters out raw thinking_log, prompts, and LLM text generation content.
    Returns None for irrelevant or sensitive frames.
    """
    if not isinstance(raw_event, dict):
        return None

    event_type = raw_event.get("event_type")
    agent_name = raw_event.get("agent_name") or ""
    tool_name = raw_event.get("tool_name") or ""
    timestamp = raw_event.get("timestamp") or datetime.now(timezone.utc).isoformat()

    # 1. Manager Started
    if event_type == "agent_process_start" and agent_name == "MEMORA Manager":
        return {
            "event_type": "manager_started",
            "agent_name": "MEMORA Manager",
            "timestamp": timestamp,
            "status": "in_progress",
        }

    # 2. Worker Invocation Started
    # Case A: tool_called on Manager with agent_tool_<agent_id>
    if event_type == "tool_called" and tool_name.startswith("agent_tool_"):
        worker_id = tool_name.replace("agent_tool_", "").strip()
        if worker_id in KNOWN_WORKERS:
            return {
                "event_type": "worker_started",
                "agent_name": KNOWN_WORKERS[worker_id],
                "agent_id": worker_id,
                "timestamp": timestamp,
                "status": "in_progress",
            }

    # Case B: agent_process_start on sub-agent
    if event_type == "agent_process_start" and agent_name in NAME_TO_ID:
        return {
            "event_type": "worker_started",
            "agent_name": agent_name,
            "agent_id": NAME_TO_ID[agent_name],
            "timestamp": timestamp,
            "status": "in_progress",
        }

    # 3. Worker Invocation Completed
    # Case A: agent_process_end on sub-agent
    if event_type == "agent_process_end" and agent_name in NAME_TO_ID:
        return {
            "event_type": "worker_completed",
            "agent_name": agent_name,
            "agent_id": NAME_TO_ID[agent_name],
            "timestamp": timestamp,
            "status": "completed",
        }

    # Case B: tool_output on Manager for agent_tool_<agent_id>
    if event_type == "tool_output" and tool_name.startswith("agent_tool_"):
        worker_id = tool_name.replace("agent_tool_", "").strip()
        if worker_id in KNOWN_WORKERS:
            return {
                "event_type": "worker_completed",
                "agent_name": KNOWN_WORKERS[worker_id],
                "agent_id": worker_id,
                "timestamp": timestamp,
                "status": "completed",
            }

    # 4. Manager Completed (synthesis finished)
    if event_type == "process_complete" and (agent_name == "MEMORA Manager" or not agent_name):
        return {
            "event_type": "manager_completed",
            "agent_name": "MEMORA Manager",
            "timestamp": timestamp,
            "status": "completed",
        }

    # 5. Workflow Completed (full agent process end for Manager)
    if event_type == "agent_process_end" and agent_name == "MEMORA Manager":
        return {
            "event_type": "workflow_completed",
            "agent_name": "MEMORA Manager",
            "timestamp": timestamp,
            "status": "completed",
        }

    # Ignore all other internal events (thinking_log, llm_generation, tool_calling_iteration, etc.)
    return None


class TelemetryCollector:
    """
    Background worker that connects to Lyzr's WebSocket metrics stream,
    captures execution events during an inference call, and processes them
    into a sanitized multi-agent telemetry summary.
    """

    def __init__(
        self,
        session_id: str,
        api_key: Optional[str] = None,
        ws_url: Optional[str] = None,
        connect_timeout: float = 4.0,
    ):
        self.session_id = session_id
        self.api_key = api_key or os.getenv("LYZR_API_KEY", "")
        self.ws_url = ws_url or DEFAULT_WS_URL_TEMPLATE.format(session_id=session_id)
        self.connect_timeout = connect_timeout

        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._connected = threading.Event()
        self._finished = threading.Event()

        self._raw_events: List[Dict[str, Any]] = []
        self._error: Optional[str] = None

    def start(self):
        """Starts the background telemetry listener thread."""
        if not self.api_key:
            self._error = "LYZR_API_KEY not provided"
            return

        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"telemetry-{self.session_id[:8]}",
            daemon=True,
        )
        self._thread.start()

        # Wait briefly for connection establishment (max 1.0 second, non-blocking failure)
        self._connected.wait(timeout=1.0)

    def _run_loop(self):
        """Thread worker executing asyncio WebSocket listener loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()

        try:
            self._loop.run_until_complete(self._listen())
        except Exception as e:
            self._error = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"[Telemetry] Listener loop error: {self._error}")
        finally:
            try:
                # Cancel pending tasks safely
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception:
                pass
            self._finished.set()

    async def _listen(self):
        """Asynchronous WebSocket receiver."""
        headers = {"x-api-key": self.api_key}
        try:
            async with websockets.connect(
                self.ws_url,
                additional_headers=headers,
                open_timeout=self.connect_timeout,
            ) as ws:
                self._connected.set()
                logger.info(f"[Telemetry] Connected to WebSocket for session '{self.session_id}'")

                while not self._stop_event.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        try:
                            data = json.loads(msg)
                            if isinstance(data, dict):
                                self._raw_events.append(data)
                        except json.JSONDecodeError:
                            continue
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed:
                        break
        except Exception as e:
            self._error = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"[Telemetry] Connection failed for session '{self.session_id}': {type(e).__name__}")
        finally:
            self._connected.set()

    def stop(self, wait_seconds: float = 2.5) -> Dict[str, Any]:
        """
        Signals listener to stop, waits for trailing messages up to wait_seconds,
        and produces the sanitized telemetry result.
        """
        # Let trailing events stream in from server-side completion
        if self._connected.is_set() and not self._error:
            time.sleep(min(wait_seconds, 3.0))

        if self._loop and self._stop_event and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop_event.set)

        if self._thread and self._thread.is_alive():
            self._finished.wait(timeout=1.0)

        return self._process_telemetry()

    def _process_telemetry(self) -> Dict[str, Any]:
        """Normalizes and dedupes execution trace frames."""
        execution_trace: List[Dict[str, Any]] = []
        seen_events = set()
        active_workers: Dict[str, Dict[str, Any]] = {}

        for raw in self._raw_events:
            norm = normalize_telemetry_event(raw)
            if not norm:
                continue

            etype = norm["event_type"]
            worker_id = norm.get("agent_id")

            # Dedup key
            dedup_key = f"{etype}:{worker_id or ''}"
            if dedup_key in seen_events:
                # Still update worker status if completing
                if etype == "worker_completed" and worker_id in active_workers:
                    active_workers[worker_id]["status"] = "completed"
                continue

            seen_events.add(dedup_key)
            execution_trace.append(norm)

            if etype == "worker_started" and worker_id:
                active_workers[worker_id] = {
                    "agent_id": worker_id,
                    "agent_name": norm["agent_name"],
                    "status": "in_progress",
                }
            elif etype == "worker_completed" and worker_id:
                if worker_id in active_workers:
                    active_workers[worker_id]["status"] = "completed"
                else:
                    active_workers[worker_id] = {
                        "agent_id": worker_id,
                        "agent_name": norm["agent_name"],
                        "status": "completed",
                    }

        workers_invoked = list(active_workers.values())
        delegation_observed = len(workers_invoked) > 0

        telemetry_status = "collected" if execution_trace else ("unavailable" if self._error else "empty")

        return {
            "telemetry_status": telemetry_status,
            "delegation_observed": delegation_observed,
            "workers_invoked": workers_invoked,
            "execution_trace": execution_trace,
            "error": self._error,
        }
