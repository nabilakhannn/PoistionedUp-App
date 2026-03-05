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
import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("app.services.gateway_ws")

# Protocol constants
PROTOCOL_VERSION = 3
CONNECT_TIMEOUT = 10  # seconds for handshake
RESPONSE_TIMEOUT = 55  # seconds for agent responses (Vercel has ~60s limit)

# Pre-registered gateway-client device credentials (from VPS identity/device.json)
_DEVICE_ID = "db3d12bfa504d70ceee68715b6841a0d620073995cfd7dee2cf85cd6d39cd4c4"
_DEVICE_PUBKEY = "SAILTafH0W2hpC2joedqhxCX7lVJV45e72z7YizSwCg"
_DEVICE_TOKEN = "ZBvmHYRqgo9rdyGldoU0wQSh7xxJ8xbtwIudtHXcq1Y"
_CLIENT_ID = "gateway-client"
_CLIENT_MODE = "backend"
_ROLE = "operator"
_SCOPES = ["operator.read", "operator.write"]


def _load_private_key():
    """Load the Ed25519 private key from env or inline base64."""
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
    except ImportError:
        return None
    key_b64 = os.environ.get("OPENCLAW_DEVICE_PRIVATE_KEY_B64", "")
    if not key_b64:
        # Inline fallback (same key stored in env)
        key_b64 = "MC4CAQAwBQYDK2VwBCIEIB0h4w/zwCTNesjOumxYMXLhSgk43BsH8ZMTBuhoSIiT"
    try:
        pem = f"-----BEGIN PRIVATE KEY-----\n{key_b64}\n-----END PRIVATE KEY-----\n"
        return load_pem_private_key(pem.encode(), password=None)
    except Exception as e:
        logger.warning("Failed to load device private key: %s", e)
        return None


def _sign_connect_payload(nonce: str, signed_at_ms: int) -> Optional[str]:
    """Build the v3 auth payload and sign it with the device private key."""
    priv_key = _load_private_key()
    if priv_key is None:
        return None
    scopes_str = ",".join(_SCOPES)
    payload = "|".join([
        "v3", _DEVICE_ID, _CLIENT_ID, _CLIENT_MODE, _ROLE,
        scopes_str, str(signed_at_ms), _DEVICE_TOKEN, nonce,
        "linux", "",  # platform, deviceFamily
    ])
    sig_bytes = priv_key.sign(payload.encode("utf-8"))
    return base64.urlsafe_b64encode(sig_bytes).rstrip(b"=").decode()


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


def _make_connect_params(nonce: str) -> Dict[str, Any]:
    """Build the connect request params including Ed25519 device signature."""
    signed_at_ms = int(time.time() * 1000)
    signature = _sign_connect_payload(nonce, signed_at_ms)

    device: Dict[str, Any] = {
        "id": _DEVICE_ID,
        "publicKey": _DEVICE_PUBKEY,
        "nonce": nonce,
        "signedAt": signed_at_ms,
    }
    if signature:
        device["signature"] = signature

    return {
        "minProtocol": PROTOCOL_VERSION,
        "maxProtocol": PROTOCOL_VERSION,
        "client": {
            "id": _CLIENT_ID,
            "displayName": "PositionedUp API",
            "version": "1.0.0",
            "platform": "linux",
            "mode": _CLIENT_MODE,
        },
        "role": _ROLE,
        "scopes": _SCOPES,
        "device": device,
        "auth": {"token": _DEVICE_TOKEN},
    }


async def _connect_and_handshake(ws: Any) -> Dict[str, Any]:
    """Perform the OpenClaw WebSocket handshake.

    1. Receive connect.challenge from server (contains nonce)
    2. Sign nonce with Ed25519 device key, send connect request
    3. Receive hello-ok response

    Returns the hello-ok payload.
    """
    # Step 1: Receive challenge
    raw = await asyncio.wait_for(ws.recv(), timeout=CONNECT_TIMEOUT)
    challenge = json.loads(raw)
    nonce = ""
    if challenge.get("type") == "event" and challenge.get("event") == "connect.challenge":
        nonce = challenge.get("payload", {}).get("nonce", "")
    else:
        logger.debug("Unexpected first message: %s", challenge.get("type"))

    # Step 2: Send connect with signed device credentials
    connect_req = {
        "type": "req",
        "id": "handshake-1",
        "method": "connect",
        "params": _make_connect_params(nonce),
    }
    await ws.send(json.dumps(connect_req))

    # Step 3: Receive hello-ok
    raw = await asyncio.wait_for(ws.recv(), timeout=CONNECT_TIMEOUT)
    hello = json.loads(raw)

    if hello.get("type") == "res" and hello.get("ok"):
        return hello.get("payload", {})

    # Handle error response
    error = hello.get("error", {})
    error_msg = error.get("message", "Handshake failed") if isinstance(error, dict) else str(error)
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
