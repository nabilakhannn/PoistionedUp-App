"""OpenClaw Gateway WebSocket Client: JSON-RPC v3 protocol.

Implements the OpenClaw 2026.2.26+ WebSocket protocol for:
- Connection handshake (connect.challenge → connect → hello-ok)
- Agent listing via `agents.list`
- Session listing via `sessions.list`
- Message sending via `chat.send` (with streaming response collection)
- Health check via `gateway.health`

This module provides one-shot WebSocket connections: connect, perform action,
collect response, disconnect. This works within Vercel's serverless timeout
(~30s for most operations, ~60s for chat.send with longer agent responses).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("app.services.gateway_ws")

# Protocol constants
PROTOCOL_VERSION = 3
CONNECT_TIMEOUT = 10  # seconds for handshake
RESPONSE_TIMEOUT = 55  # seconds for agent responses (Vercel has ~60s limit)


class GatewayWSError(Exception):
    """Raised when a WebSocket operation fails."""

    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


def _get_ws_url() -> str:
    """Convert the HTTP gateway URL to a WebSocket URL."""
    url = settings.openclaw_gateway_url.rstrip("/")
    if not url:
        raise GatewayWSError("OpenClaw gateway URL not configured.")
    return url.replace("http://", "ws://").replace("https://", "wss://")


def _make_connect_params() -> Dict[str, Any]:
    """Build the connect request params for the handshake."""
    params: Dict[str, Any] = {
        "minProtocol": PROTOCOL_VERSION,
        "maxProtocol": PROTOCOL_VERSION,
        "client": {
            "id": "positionedup-api",
            "displayName": "PositionedUp API",
            "version": "1.0.0",
            "platform": "linux",
            "mode": "backend",
        },
        "role": "operator",
        "scopes": ["operator.read", "operator.write"],
        "device": {
            "id": f"positionedup-api-{uuid.uuid4().hex[:8]}",
        },
    }
    # Include auth token if configured
    if settings.openclaw_gateway_token:
        params["auth"] = {"token": settings.openclaw_gateway_token}
    else:
        params["auth"] = {}
    return params


async def _connect_and_handshake(ws: Any) -> Dict[str, Any]:
    """Perform the OpenClaw WebSocket handshake.

    1. Receive connect.challenge from server
    2. Send connect request
    3. Receive hello-ok response

    Returns the hello-ok payload.
    """
    # Step 1: Receive challenge
    raw = await asyncio.wait_for(ws.recv(), timeout=CONNECT_TIMEOUT)
    challenge = json.loads(raw)
    if challenge.get("type") != "event" or challenge.get("event") != "connect.challenge":
        logger.debug("Unexpected first message: %s", challenge.get("type"))
        # Some versions may not send a challenge — proceed anyway

    # Step 2: Send connect
    connect_req = {
        "type": "req",
        "id": "handshake-1",
        "method": "connect",
        "params": _make_connect_params(),
    }
    await ws.send(json.dumps(connect_req))

    # Step 3: Receive hello-ok
    raw = await asyncio.wait_for(ws.recv(), timeout=CONNECT_TIMEOUT)
    hello = json.loads(raw)

    if hello.get("type") == "res" and hello.get("ok"):
        return hello.get("payload", {})

    # Handle error response
    error_msg = hello.get("payload", {}).get("message", "Handshake failed")
    raise GatewayWSError(f"Gateway handshake failed: {error_msg}")


async def _send_rpc(ws: Any, method: str, params: Dict[str, Any], timeout: float = 30) -> Dict[str, Any]:
    """Send an RPC request and wait for the matching response."""
    req_id = str(uuid.uuid4())[:8]
    request = {
        "type": "req",
        "id": req_id,
        "method": method,
        "params": params,
    }
    await ws.send(json.dumps(request))

    # Wait for matching response (skip events)
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise GatewayWSError(f"Timeout waiting for {method} response")

        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        msg = json.loads(raw)

        if msg.get("type") == "res" and msg.get("id") == req_id:
            if msg.get("ok"):
                return msg.get("payload", {})
            error = msg.get("payload", {}).get("message", "Unknown error")
            raise GatewayWSError(f"RPC {method} failed: {error}")

        # Skip events (ticks, broadcasts, etc.)


# ── Public API ─────────────────────────────────────────────


async def ws_check_health() -> Dict[str, Any]:
    """Check gateway health via WebSocket RPC."""
    try:
        import websockets
    except ImportError:
        raise GatewayWSError("websockets package not installed")

    ws_url = _get_ws_url()
    try:
        async with websockets.connect(ws_url, open_timeout=CONNECT_TIMEOUT) as ws:
            await _connect_and_handshake(ws)
            result = await _send_rpc(ws, "gateway.health", {}, timeout=10)
            return {
                "connected": True,
                "status": "healthy",
                "protocol": "websocket",
                "version": result.get("version", "unknown"),
                "uptime": result.get("uptime"),
                "agents_loaded": result.get("agentsLoaded"),
            }
    except GatewayWSError:
        raise
    except Exception as e:
        logger.debug("WebSocket health check failed: %s", e)
        raise GatewayWSError(f"WebSocket connection failed: {e}")


async def ws_list_agents() -> List[Dict[str, Any]]:
    """List agents via WebSocket RPC."""
    try:
        import websockets
    except ImportError:
        raise GatewayWSError("websockets package not installed")

    ws_url = _get_ws_url()
    try:
        async with websockets.connect(ws_url, open_timeout=CONNECT_TIMEOUT) as ws:
            await _connect_and_handshake(ws)
            result = await _send_rpc(ws, "agents.list", {}, timeout=10)
            agents = result.get("agents", [])
            return [
                {
                    "id": a.get("id", "unknown"),
                    "name": a.get("name", a.get("id", "unknown")),
                    "status": "loaded",
                    "is_default": result.get("defaultId") == a.get("id"),
                }
                for a in agents
            ]
    except GatewayWSError:
        raise
    except Exception as e:
        logger.debug("WebSocket agents list failed: %s", e)
        raise GatewayWSError(f"WebSocket agents list failed: {e}")


async def ws_list_sessions() -> List[Dict[str, Any]]:
    """List sessions via WebSocket RPC."""
    try:
        import websockets
    except ImportError:
        raise GatewayWSError("websockets package not installed")

    ws_url = _get_ws_url()
    try:
        async with websockets.connect(ws_url, open_timeout=CONNECT_TIMEOUT) as ws:
            await _connect_and_handshake(ws)
            result = await _send_rpc(ws, "sessions.list", {}, timeout=10)
            sessions = result if isinstance(result, list) else result.get("sessions", [])
            return [
                {
                    "id": s.get("id", "unknown"),
                    "agent_id": s.get("agentId"),
                    "status": s.get("status", "unknown"),
                    "created_at": s.get("createdAt"),
                    "last_activity": s.get("lastActivity"),
                    "message_count": s.get("messageCount"),
                }
                for s in sessions[:50]
            ]
    except GatewayWSError:
        raise
    except Exception as e:
        logger.debug("WebSocket sessions list failed: %s", e)
        raise GatewayWSError(f"WebSocket sessions list failed: {e}")


async def ws_send_message(
    agent_id: str,
    message: str,
    *,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a message to an agent via WebSocket and collect the full response.

    Uses chat.send RPC method, then collects streaming chat events until
    the final response arrives.

    Args:
        agent_id: Target agent (e.g. "jumbo", "copywriter").
        message: The user message text.
        session_id: Optional session to continue.

    Returns:
        Dict with session_id, response text, agent_id, and status.
    """
    try:
        import websockets
    except ImportError:
        raise GatewayWSError("websockets package not installed")

    ws_url = _get_ws_url()
    session_key = f"agent:{agent_id}:api:positionedup"
    if session_id:
        session_key = session_id

    try:
        async with websockets.connect(ws_url, open_timeout=CONNECT_TIMEOUT) as ws:
            await _connect_and_handshake(ws)

            # Send chat.send request
            idempotency_key = str(uuid.uuid4())
            req_id = str(uuid.uuid4())[:8]
            request = {
                "type": "req",
                "id": req_id,
                "method": "chat.send",
                "params": {
                    "sessionKey": session_key,
                    "message": message[:10000],
                    "idempotencyKey": idempotency_key,
                    "deliver": True,
                },
            }
            await ws.send(json.dumps(request))

            # Collect response: first the RPC ack, then streaming events
            run_id = None
            response_chunks: list[str] = []
            final_response: Optional[str] = None

            deadline = asyncio.get_event_loop().time() + RESPONSE_TIMEOUT
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    # Return partial response if we have chunks
                    if response_chunks:
                        return {
                            "session_id": session_key,
                            "agent_id": agent_id,
                            "status": "partial",
                            "response": "".join(response_chunks),
                        }
                    raise GatewayWSError("Agent response timed out (55s)")

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except asyncio.TimeoutError:
                    if response_chunks:
                        return {
                            "session_id": session_key,
                            "agent_id": agent_id,
                            "status": "partial",
                            "response": "".join(response_chunks),
                        }
                    raise GatewayWSError("Agent response timed out (55s)")

                msg = json.loads(raw)

                # Handle RPC response (ack)
                if msg.get("type") == "res" and msg.get("id") == req_id:
                    if not msg.get("ok"):
                        error = msg.get("payload", {}).get("message", "Unknown error")
                        raise GatewayWSError(f"chat.send failed: {error}")
                    payload = msg.get("payload", {})
                    run_id = payload.get("runId")
                    continue

                # Handle chat streaming events
                if msg.get("type") == "event" and msg.get("event") == "chat":
                    payload = msg.get("payload", {})
                    state = payload.get("state")
                    content = payload.get("message", {}).get("content", "")

                    if state == "delta" and content:
                        response_chunks.append(content)
                    elif state == "final":
                        final_response = content or "".join(response_chunks)
                        break
                    elif state in ("aborted", "error"):
                        error_msg = payload.get("error", "Agent aborted")
                        raise GatewayWSError(f"Agent error: {error_msg}")

                # Skip other events (ticks, etc.)

            return {
                "session_id": session_key,
                "agent_id": agent_id,
                "status": "delivered",
                "response": final_response,
                "run_id": run_id,
            }

    except GatewayWSError:
        raise
    except Exception as e:
        logger.warning("WebSocket message send failed: %s", e)
        raise GatewayWSError(f"WebSocket message failed: {e}")
