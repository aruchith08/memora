"""
Omi Notification Service for MEMORA.
Dispatches push notification responses to the user's Omi app via
the official Omi Integrations API:
POST https://api.omi.me/v2/integrations/{app_id}/notification?uid={uid}&message={message}
"""

import os
import logging
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("memora-omi-notification")

OMI_API_BASE = "https://api.omi.me/v2/integrations"


def get_omi_notification_config() -> Dict[str, str]:
    """
    Validate and retrieve Omi notification credentials from environment variables.
    Raises ValueError if required configurations are absent.
    """
    app_id = os.getenv("OMI_APP_ID", "").strip()
    app_secret = os.getenv("OMI_APP_SECRET", "").strip()

    if not app_id:
        raise ValueError("OMI_APP_ID is not configured in environment variables.")
    if not app_secret:
        raise ValueError("OMI_APP_SECRET is not configured in environment variables.")

    return {
        "app_id": app_id,
        "app_secret": app_secret,
    }


def send_omi_notification(
    uid: str,
    message: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    """
    Sends a push notification message to the specified Omi user.
    Never exposes or logs OMI_APP_SECRET.
    Returns structured result dict: {"status": "sent" | "failed" | "skipped", "uid": uid, "error": ...}
    """
    if not uid or not uid.strip():
        return {
            "status": "skipped",
            "uid": uid,
            "error": "Empty or invalid uid.",
            "status_code": None,
        }

    clean_message = message.strip() if message else ""
    if not clean_message:
        return {
            "status": "skipped",
            "uid": uid,
            "error": "Cannot send empty notification message.",
            "status_code": None,
        }

    # Resolve credentials
    try:
        config = get_omi_notification_config()
        effective_app_id = (app_id or config["app_id"]).strip()
        effective_app_secret = (app_secret or config["app_secret"]).strip()
    except ValueError as ve:
        logger.error(f"[Omi Notification] Configuration error: {ve}")
        return {
            "status": "failed",
            "uid": uid,
            "error": str(ve),
            "status_code": None,
        }

    endpoint = f"{OMI_API_BASE}/{effective_app_id}/notification"
    params = {
        "uid": uid.strip(),
        "message": clean_message,
    }
    headers = {
        "Authorization": f"Bearer {effective_app_secret}",
        "Content-Type": "application/json",
    }

    logger.info(
        f"[Omi Notification] Sending push notification to uid='{uid}' "
        f"(app_id='{effective_app_id[:6]}...', message_chars={len(clean_message)})"
    )

    try:
        response = requests.post(
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    except requests.Timeout:
        logger.error("[Omi Notification] Request timed out.")
        return {
            "status": "failed",
            "uid": uid,
            "error": "Omi notification request timed out.",
            "status_code": None,
        }
    except requests.RequestException as e:
        logger.error(f"[Omi Notification] Network error: {type(e).__name__}")
        return {
            "status": "failed",
            "uid": uid,
            "error": f"Omi notification network error: {type(e).__name__}",
            "status_code": None,
        }

    if response.status_code not in (200, 201):
        logger.error(f"[Omi Notification] Failed with HTTP {response.status_code}")
        return {
            "status": "failed",
            "uid": uid,
            "error": f"Omi API returned HTTP {response.status_code}",
            "status_code": response.status_code,
        }

    logger.info(f"[Omi Notification] Successfully delivered to uid='{uid}' (HTTP {response.status_code})")
    return {
        "status": "sent",
        "uid": uid,
        "error": None,
        "status_code": response.status_code,
    }
