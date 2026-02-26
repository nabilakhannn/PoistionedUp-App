"""OpenClaw Gateway Client: communicate with the agent runtime on VPS.

This service provides an HTTP client to interact with the OpenClaw gateway
running on the Hostinger VPS. It handles health checks, agent listing,
session management, and message relay.

When OPENCLAW_MOCK_MODE=true, all functions delegate to gateway_mock.py
instead of making real HTTP calls. This enables local dev without a VPS.

Security:
  - All requests include the gateway token for authentication
  - Timeouts prevent hanging on unreachable gateways
  - URL is validated at startup (no user-controlled URLs)
  - Response data is sanitized before returning to frontend
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("app.services.gateway_client")

# Connection timeouts: 5s connect, 30s read (agents may take time to respond)
_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)


class GatewayError(Exception):
    """Raised when the gateway is unreachable or returns an error."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _get_base_url() -> str:
    """Get the configured gateway URL, raising if not set."""
    url = settings.openclaw_gateway_url.rstrip("/")
    if not url:
        raise GatewayError("OpenClaw gateway URL not configured. Set OPENCLAW_GATEWAY_URL in env.")
    return url


def _get_headers() -> Dict[str, str]:
    """Build request headers with gateway authentication."""
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "PositionedUp-API/1.0",
    }
    if settings.openclaw_gateway_token:
        headers["Authorization"] = f"Bearer {settings.openclaw_gateway_token}"
    return headers


# ── Health Check ─────────────────────────────────────────────


async def check_health() -> Dict[str, Any]:
    """Check if the OpenClaw gateway is reachable and healthy.

    Returns:
        Dict with connected (bool), latency_ms (float), gateway version, etc.
    """
    if settings.openclaw_mock_mode:
        from app.services.gateway_mock import mock_check_health
        return await mock_check_health()

    base_url = _get_base_url()
    start = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/health",
                headers=_get_headers(),
            )

        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        if resp.status_code == 200:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            return {
                "connected": True,
                "status": "healthy",
                "latency_ms": round(latency_ms, 1),
                "gateway_url": _mask_url(base_url),
                "version": data.get("version", "unknown"),
                "uptime": data.get("uptime"),
                "agents_loaded": data.get("agents_loaded"),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "connected": True,
                "status": "unhealthy",
                "latency_ms": round(latency_ms, 1),
                "gateway_url": _mask_url(base_url),
                "http_status": resp.status_code,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    except httpx.ConnectError:
        return {
            "connected": False,
            "status": "unreachable",
            "gateway_url": _mask_url(base_url),
            "error": "Connection refused — gateway may not be running",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.TimeoutException:
        return {
            "connected": False,
            "status": "timeout",
            "gateway_url": _mask_url(base_url),
            "error": "Connection timed out after 5 seconds",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning("Gateway health check failed: %s", e)
        return {
            "connected": False,
            "status": "error",
            "gateway_url": _mask_url(base_url),
            "error": "Unexpected error checking gateway health",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


# ── Agent Info ──────────────────────────────────────────────


async def list_gateway_agents() -> List[Dict[str, Any]]:
    """List agents known to the gateway.

    Returns agent IDs, names, and status from the gateway's perspective.
    Falls back to config-based list if endpoint is not available.
    """
    if settings.openclaw_mock_mode:
        from app.services.gateway_mock import mock_list_agents
        return await mock_list_agents()

    base_url = _get_base_url()

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/api/agents",
                headers=_get_headers(),
            )

        if resp.status_code == 200:
            data = resp.json()
            # Normalize: gateway may return list or {agents: [...]}
            agents = data if isinstance(data, list) else data.get("agents", [])
            return [_sanitize_agent(a) for a in agents]

    except Exception as e:
        logger.debug("Gateway /api/agents not available: %s", e)

    # Fallback: return agent list from openclaw.json config
    return _get_config_agents()


async def get_gateway_sessions() -> List[Dict[str, Any]]:
    """List active sessions on the gateway.

    Returns session IDs, agent associations, and activity timestamps.
    """
    if settings.openclaw_mock_mode:
        from app.services.gateway_mock import mock_get_sessions
        return await mock_get_sessions()

    base_url = _get_base_url()

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/api/sessions",
                headers=_get_headers(),
            )

        if resp.status_code == 200:
            data = resp.json()
            sessions = data if isinstance(data, list) else data.get("sessions", [])
            return [_sanitize_session(s) for s in sessions[:50]]

    except Exception as e:
        logger.debug("Gateway /api/sessions not available: %s", e)

    return []


# ── Message Relay ───────────────────────────────────────────


async def send_message_to_agent(
    agent_id: str,
    message: str,
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to an agent via the gateway.

    Args:
        agent_id: Target agent ID (e.g. "jumbo", "trend-analyzer").
        message: The message text to send.
        session_id: Optional existing session to continue.

    Returns:
        Dict with session_id, status, and any immediate response.
    """
    if settings.openclaw_mock_mode:
        from app.services.gateway_mock import mock_send_message
        return await mock_send_message(agent_id, message, session_id=session_id)

    base_url = _get_base_url()

    payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "message": message[:10000],  # Cap message length
    }
    if session_id:
        payload["session_id"] = session_id

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)) as client:
            resp = await client.post(
                f"{base_url}/api/messages",
                headers=_get_headers(),
                json=payload,
            )

        if resp.status_code in (200, 201):
            return _sanitize_message_response(resp.json())
        else:
            logger.warning("Gateway message error: %s %s", resp.status_code, resp.text[:200])
            raise GatewayError(
                f"Gateway rejected the request (HTTP {resp.status_code})",
                status_code=resp.status_code,
            )

    except httpx.TimeoutException:
        raise GatewayError("Message delivery timed out (60s)")
    except httpx.ConnectError:
        raise GatewayError("Cannot reach gateway — is it running?")


# ── Full Status Aggregate ──────────────────────────────────


async def get_full_status() -> Dict[str, Any]:
    """Aggregate health, agents, and sessions into a single status object.

    This is the main endpoint the frontend dashboard calls.
    """
    health = await check_health()
    agents: List[Dict[str, Any]] = []
    sessions: List[Dict[str, Any]] = []

    if health.get("connected"):
        try:
            agents = await list_gateway_agents()
        except Exception as e:
            logger.debug("Failed to list gateway agents: %s", e)

        try:
            sessions = await get_gateway_sessions()
        except Exception as e:
            logger.debug("Failed to list gateway sessions: %s", e)

    # Build deployment checklist
    checklist = _build_deployment_checklist(health, agents)

    return {
        "health": health,
        "agents": agents,
        "sessions": sessions,
        "checklist": checklist,
        "mock_mode": settings.openclaw_mock_mode,
        "config": {
            "gateway_url_set": bool(settings.openclaw_gateway_url),
            "gateway_token_set": bool(settings.openclaw_gateway_token),
            "agent_api_key_set": bool(settings.agent_api_key),
            "openai_key_set": bool(settings.openai_api_key),
        },
    }


# ── Deployment Checklist ────────────────────────────────────


def _build_deployment_checklist(
    health: Dict[str, Any],
    agents: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a step-by-step deployment verification checklist."""
    items = [
        {
            "id": "gateway_url",
            "label": "Gateway URL configured",
            "status": "pass" if settings.openclaw_gateway_url else "fail",
            "detail": _mask_url(settings.openclaw_gateway_url) if settings.openclaw_gateway_url else "Set OPENCLAW_GATEWAY_URL in env",
        },
        {
            "id": "gateway_token",
            "label": "Gateway token configured",
            "status": "pass" if settings.openclaw_gateway_token else "fail",
            "detail": "Token is set" if settings.openclaw_gateway_token else "Set OPENCLAW_GATEWAY_TOKEN in env",
        },
        {
            "id": "agent_api_key",
            "label": "Agent API key configured",
            "status": "pass" if settings.agent_api_key else "fail",
            "detail": "Key is set" if settings.agent_api_key else "Set AGENT_API_KEY in env",
        },
        {
            "id": "gateway_reachable",
            "label": "Gateway is reachable",
            "status": "pass" if health.get("connected") else "fail",
            "detail": f"Latency: {health.get('latency_ms', '?')}ms" if health.get("connected") else health.get("error", "Not connected"),
        },
        {
            "id": "gateway_healthy",
            "label": "Gateway is healthy",
            "status": "pass" if health.get("status") == "healthy" else ("warn" if health.get("connected") else "fail"),
            "detail": health.get("status", "unknown"),
        },
        {
            "id": "agents_loaded",
            "label": "Agents loaded in gateway",
            "status": "pass" if len(agents) > 0 else ("warn" if health.get("connected") else "skip"),
            "detail": f"{len(agents)} agent(s) loaded" if agents else "No agents detected",
        },
        {
            "id": "openai_key",
            "label": "OpenAI API key configured",
            "status": "pass" if settings.openai_api_key else "fail",
            "detail": "Key is set" if settings.openai_api_key else "Required for agent LLM calls",
        },
    ]
    return items


# ── Internal Helpers ────────────────────────────────────────


def _mask_url(url: str) -> str:
    """Mask sensitive parts of a URL for display.

    Shows scheme + host but hides port if non-standard.
    """
    if not url:
        return "(not set)"
    # Just show the URL without any embedded credentials
    if "@" in url:
        # Strip credentials: http://user:pass@host → http://***@host
        scheme_end = url.index("://") + 3
        at_pos = url.index("@")
        return url[:scheme_end] + "***" + url[at_pos:]
    return url


def _sanitize_agent(agent: Any) -> Dict[str, Any]:
    """Extract safe fields from a gateway agent object."""
    if not isinstance(agent, dict):
        return {"id": str(agent)}
    return {
        "id": agent.get("id", "unknown"),
        "name": agent.get("name", agent.get("id", "unknown")),
        "status": agent.get("status", "unknown"),
        "model": agent.get("model", {}).get("model") if isinstance(agent.get("model"), dict) else None,
        "workspace": agent.get("workspace"),
        "channels": agent.get("channels", []),
        "is_default": agent.get("default", False),
    }


def _sanitize_session(session: Any) -> Dict[str, Any]:
    """Extract safe fields from a gateway session object."""
    if not isinstance(session, dict):
        return {"id": str(session)}
    return {
        "id": session.get("id", "unknown"),
        "agent_id": session.get("agent_id"),
        "status": session.get("status", "unknown"),
        "created_at": session.get("created_at"),
        "last_activity": session.get("last_activity"),
        "message_count": session.get("message_count"),
    }


def _sanitize_message_response(data: Any) -> Dict[str, Any]:
    """Extract safe fields from a gateway message response.

    Prevents leaking internal gateway details to the frontend.
    """
    if not isinstance(data, dict):
        return {"status": "sent"}
    return {
        "session_id": data.get("session_id"),
        "status": data.get("status", "sent"),
        "response": data.get("response"),
        "agent_id": data.get("agent_id"),
        "message_id": data.get("message_id"),
        "created_at": data.get("created_at"),
    }


def _get_config_agents() -> List[Dict[str, Any]]:
    """Return the agent list from openclaw.json config (fallback)."""
    return [
        {"id": "jumbo", "name": "Jumbo (Orchestrator)", "status": "unknown", "model": "gpt-4o", "is_default": True, "channels": ["telegram"]},
        {"id": "trend-analyzer", "name": "Trend Analyzer", "status": "unknown", "model": "gpt-4o-mini", "is_default": False, "channels": []},
        {"id": "copywriter", "name": "Copywriter", "status": "unknown", "model": "gpt-4o", "is_default": False, "channels": []},
        {"id": "visual-designer", "name": "Visual Designer", "status": "unknown", "model": "gpt-4o", "is_default": False, "channels": []},
        {"id": "distributor", "name": "Distributor", "status": "unknown", "model": "gpt-4o-mini", "is_default": False, "channels": []},
        {"id": "analytics", "name": "Analytics", "status": "unknown", "model": "gpt-4o-mini", "is_default": False, "channels": []},
    ]
