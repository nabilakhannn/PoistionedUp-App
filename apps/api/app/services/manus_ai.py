"""Manus AI Client — Slice 109.

Optional BYOK integration with Manus AI for research-heavy workflows.
Only used when user has configured their Manus API key AND explicitly
toggles "Use Manus" on a manus_beneficial workflow.

Built-in AI (Claude Sonnet 4.6 + Perplexity + Gemini) is the primary
engine for all workflows. Manus is an optional upgrade for autonomous
web research tasks only.

API Reference: https://api.manus.im/v1
Auth: Bearer token (user's API key)
Pattern: Create task → poll status → get result (async)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.deps import get_admin_client

logger = logging.getLogger("app.services.manus_ai")

BASE_URL = "https://api.manus.im/v1"
POLL_TIMEOUT_SECONDS = 600  # 10 minutes
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]  # exponential backoff


class ManusAIClient:
    """Client for Manus AI REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def create_task(
        self,
        prompt: str,
        mode: str = "agent",
        profile: str = "quality",
        file_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new Manus task.

        Args:
            prompt: The task description/prompt
            mode: Task mode - "chat", "adaptive", or "agent"
            profile: Quality profile - "speed" or "quality"
            file_ids: Optional list of uploaded file IDs

        Returns:
            {"task_id": str, "status": str}
        """
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "mode": mode,
            "profile": profile,
        }
        if file_ids:
            payload["file_ids"] = file_ids

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BASE_URL}/tasks",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        task_id = data.get("task_id") or data.get("id", "")
        status = data.get("status", "pending")

        logger.info("Manus task created: task_id=%s status=%s", task_id, status)
        return {"task_id": task_id, "status": status}

    async def poll_task(self, task_id: str) -> Dict[str, Any]:
        """Poll a Manus task for status.

        Returns:
            {"status": str, "result_text": str|None, "error": str|None}
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/tasks/{task_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", "pending")
        result_text = None
        error = None

        if status == "completed":
            # Extract result from various possible response shapes
            result_text = (
                data.get("result", {}).get("text")
                or data.get("output")
                or data.get("result_text")
                or str(data.get("result", ""))
            )
        elif status == "failed":
            error = data.get("error", {}).get("message") or data.get("error_message", "Unknown error")

        return {"status": status, "result_text": result_text, "error": error}

    async def validate_key(self) -> bool:
        """Validate the API key by listing tasks (limit=1)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/tasks",
                    headers=self.headers,
                    params={"limit": 1},
                )
                return resp.status_code == 200
        except Exception:
            return False


def compress_brand_context(brand_context: Dict[str, Any]) -> str:
    """Compress 4500-token brand context to ~500 tokens for Manus.

    Manus doesn't understand our internal brand schema, so we serialize
    only the most important fields into a compact summary.

    For built-in AI, we inject the FULL context (no compression needed).
    """
    if not brand_context:
        return ""

    parts = []
    if brand_context.get("name"):
        parts.append(f"Brand: {brand_context['name']}")
    if brand_context.get("voice"):
        parts.append(f"Voice: {brand_context['voice']}")
    if brand_context.get("ica"):
        parts.append(f"Ideal Client: {brand_context['ica']}")
    if brand_context.get("positioning"):
        parts.append(f"Positioning: {brand_context['positioning']}")
    if brand_context.get("offer"):
        parts.append(f"Offer: {brand_context['offer']}")

    anxiety = brand_context.get("anxiety_list", [])
    if anxiety:
        parts.append(f"Top Fears: {', '.join(str(a) for a in anxiety[:5])}")

    benefits = brand_context.get("benefit_list", [])
    if benefits:
        parts.append(f"Top Desires: {', '.join(str(b) for b in benefits[:5])}")

    power_words = brand_context.get("power_words", [])
    if power_words:
        parts.append(f"Power Words: {', '.join(str(w) for w in power_words[:10])}")

    return "\n".join(parts)


async def save_manus_task(
    user_id: str,
    brand_id: str,
    workflow_slug: str,
    manus_task_id: str,
    prompt_sent: str,
) -> str:
    """Save a Manus task to the database. Returns the internal task ID."""
    sb = get_admin_client()
    result = sb.table("manus_tasks").insert({
        "user_id": user_id,
        "brand_id": brand_id,
        "workflow_slug": workflow_slug,
        "manus_task_id": manus_task_id,
        "prompt_sent": prompt_sent[:5000],
        "status": "pending",
    }).execute()

    if not result.data:
        raise RuntimeError("Failed to save Manus task")

    return result.data[0]["id"]


async def update_manus_task(
    task_id: str,
    user_id: str,
    status: str,
    result_text: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Update a Manus task status in the database."""
    sb = get_admin_client()
    update_data: Dict[str, Any] = {"status": status}

    if result_text is not None:
        update_data["result_text"] = result_text
    if error_message is not None:
        update_data["error_message"] = error_message
    if status in ("completed", "failed", "timeout"):
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    sb.table("manus_tasks").update(update_data).eq("id", task_id).eq("user_id", user_id).execute()


async def get_manus_task(task_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a Manus task by internal ID (with IDOR guard)."""
    sb = get_admin_client()
    result = (
        sb.table("manus_tasks")
        .select("*")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_manus_api_key(user_id: str) -> Optional[str]:
    """Retrieve the user's Manus API key from connectors (decrypted).

    Returns None if no key configured.
    """
    try:
        from app.services.connectors import decrypt_credentials
        sb = get_admin_client()
        result = (
            sb.table("user_connectors")
            .select("encrypted_credentials")
            .eq("user_id", user_id)
            .eq("service", "manus_ai")
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        creds = decrypt_credentials(result.data[0]["encrypted_credentials"])
        return creds.get("api_key")
    except Exception:
        return None
