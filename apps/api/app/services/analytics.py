"""PostHog analytics service for server-side event tracking.

Provides a thin wrapper around the PostHog Python SDK.
If POSTHOG_API_KEY is not set, all calls become safe no-ops.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("app.services.analytics")

# Global PostHog client (lazy-initialized)
_posthog_client = None
_initialized = False


def _get_client():
    """Lazy-initialize the PostHog client."""
    global _posthog_client, _initialized

    if _initialized:
        return _posthog_client

    _initialized = True

    try:
        from app.config import settings

        api_key = getattr(settings, "posthog_api_key", "")
        host = getattr(settings, "posthog_host", "https://us.i.posthog.com")

        if not api_key:
            logger.info("PostHog API key not set, server-side analytics disabled")
            return None

        import posthog

        posthog.project_api_key = api_key
        posthog.host = host
        # Disable debug mode in production
        posthog.debug = False
        # Use the module-level functions (posthog SDK works as a singleton)
        _posthog_client = posthog

        logger.info("PostHog server-side analytics initialized (host=%s)", host)
        return _posthog_client

    except ImportError:
        logger.warning("posthog package not installed, server-side analytics disabled")
        return None
    except Exception as e:
        logger.warning("Failed to initialize PostHog: %s", e)
        return None


def identify_user(
    user_id: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """Identify a user with PostHog, attaching properties."""
    client = _get_client()
    if not client:
        return
    try:
        client.identify(user_id, properties or {})
    except Exception as e:
        logger.debug("PostHog identify failed: %s", e)


def track_event(
    user_id: str,
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """Track a server-side event in PostHog.

    Args:
        user_id: The user's unique ID (Supabase auth user ID).
        event_name: The event name (e.g., "workflow_created").
        properties: Optional dict of event properties.
    """
    client = _get_client()
    if not client:
        return
    try:
        client.capture(
            distinct_id=user_id,
            event=event_name,
            properties=properties or {},
        )
    except Exception as e:
        logger.debug("PostHog capture failed: %s", e)


def track_llm_event(
    user_id: str,
    model: str,
    step: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: float = 0,
    workflow_id: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Track an LLM API call event with token and cost metrics.

    This creates structured events that can be analyzed in PostHog
    to understand LLM usage patterns, costs, and reliability.
    """
    properties = {
        "model": model,
        "step": step,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "success": success,
    }
    if workflow_id:
        properties["workflow_id"] = workflow_id
    if error:
        properties["error"] = error

    track_event(user_id, "llm_api_call", properties)


def track_pipeline_event(
    user_id: str,
    workflow_id: str,
    event_type: str,
    step: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """Track a content pipeline lifecycle event.

    event_type examples: pipeline_started, pipeline_completed,
    pipeline_failed, pipeline_interrupted, step_completed
    """
    props = {
        "workflow_id": workflow_id,
        "pipeline_event": event_type,
    }
    if step:
        props["step"] = step
    if properties:
        props.update(properties)

    track_event(user_id, f"pipeline_{event_type}", props)


def flush() -> None:
    """Flush any queued PostHog events. Call on shutdown."""
    client = _get_client()
    if not client:
        return
    try:
        client.flush()
    except Exception as e:
        logger.debug("PostHog flush failed: %s", e)
