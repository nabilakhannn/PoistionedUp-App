"""Gateway API: proxy endpoints for OpenClaw gateway communication.

Endpoints:
  GET  /gateway/health   — Check gateway connectivity
  GET  /gateway/status   — Full deployment status (health + agents + checklist)
  GET  /gateway/agents   — List agents from gateway
  POST /gateway/message  — Send message to an agent via gateway
  GET  /gateway/sessions — List active gateway sessions
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, CurrentUser
from app.services.gateway_client import (
    check_health,
    get_full_status,
    list_gateway_agents,
    get_gateway_sessions,
    send_message_to_agent,
    GatewayError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gateway", tags=["gateway"])


# ── Request/Response Models ──────────────────────────────────

class GatewayMessageRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = Field(None, max_length=200)


# ── Endpoints ────────────────────────────────────────────────

@router.get("/health")
async def gateway_health(user: CurrentUser = Depends(get_current_user)):
    """Check if the OpenClaw gateway is reachable and healthy."""
    try:
        return await check_health()
    except GatewayError as e:
        return {
            "connected": False,
            "status": "not_configured",
            "error": str(e),
        }


@router.get("/status")
async def gateway_status(user: CurrentUser = Depends(get_current_user)):
    """Full deployment status: health + agents + sessions + checklist.

    This is the main endpoint for the Deployment Dashboard.
    """
    try:
        return await get_full_status()
    except GatewayError as e:
        return {
            "health": {
                "connected": False,
                "status": "not_configured",
                "error": str(e),
            },
            "agents": [],
            "sessions": [],
            "checklist": [],
            "config": {
                "gateway_url_set": False,
                "gateway_token_set": False,
                "agent_api_key_set": False,
                "openai_key_set": False,
            },
        }


@router.get("/agents")
async def gateway_agents(user: CurrentUser = Depends(get_current_user)):
    """List agents known to the OpenClaw gateway."""
    try:
        return await list_gateway_agents()
    except GatewayError as e:
        raise HTTPException(503, str(e))


@router.get("/sessions")
async def gateway_sessions(user: CurrentUser = Depends(get_current_user)):
    """List active sessions on the OpenClaw gateway."""
    try:
        return await get_gateway_sessions()
    except GatewayError as e:
        raise HTTPException(503, str(e))


@router.post("/message")
async def gateway_send_message(
    body: GatewayMessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to an agent via the OpenClaw gateway.

    Returns the gateway's response (session ID, agent reply, etc.).
    """
    try:
        result = await send_message_to_agent(
            agent_id=body.agent_id,
            message=body.message,
            session_id=body.session_id,
        )
        return result
    except GatewayError as e:
        raise HTTPException(
            status_code=e.status_code if e.status_code >= 400 else 503,
            detail=str(e),
        )
