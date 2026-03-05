"""Jumbo Hub Router — Slice 107.

Persistent multi-turn chat with Jumbo (general-purpose AI partner).

Endpoints (all JWT-authenticated + IDOR-protected):
  POST   /hub/conversations                  — Create new conversation
  GET    /hub/conversations                  — List active conversations
  GET    /hub/conversations/{conversation_id} — Get full conversation
  POST   /hub/conversations/{conversation_id}/chat — Send message
  PATCH  /hub/conversations/{conversation_id}/archive — Archive
  POST   /hub/save-note                      — Save text as agent_memory

Security:
  - JWT auth via get_current_user
  - IDOR: all queries scoped by user_id
  - UUID validation on brand_id and conversation_id
  - Message capped at 5000 chars (Pydantic Field)
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.services import jumbo_hub

logger = logging.getLogger("app.routers.jumbo_hub")

router = APIRouter(tags=["jumbo-hub"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _validate_uuid(value: str, name: str = "ID") -> None:
    if not _UUID_RE.match(value):
        raise HTTPException(400, f"Invalid {name} — must be a UUID")


# ── Request / Response schemas ────────────────────────────────────────────


class CreateConversationRequest(BaseModel):
    brand_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class SaveNoteRequest(BaseModel):
    brand_id: str
    content: str = Field(..., min_length=1, max_length=10000)
    title: str = Field(default="", max_length=200)


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/hub/conversations")
async def create_conversation(
    req: CreateConversationRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new Jumbo Hub conversation."""
    _validate_uuid(req.brand_id, "brand_id")

    try:
        result = jumbo_hub.create_conversation(
            user_id=user.id,
            brand_id=req.brand_id,
        )
        return result
    except Exception as exc:
        logger.warning("create_conversation failed: %s", exc)
        raise HTTPException(500, "Failed to create conversation")


@router.get("/hub/conversations")
async def list_conversations(
    brand_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    """List active conversations for a brand."""
    _validate_uuid(brand_id, "brand_id")

    conversations = jumbo_hub.list_conversations(
        user_id=user.id,
        brand_id=brand_id,
        limit=limit,
    )
    return {"conversations": conversations}


@router.get("/hub/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get full conversation with all messages."""
    _validate_uuid(conversation_id, "conversation_id")

    conv = jumbo_hub.get_conversation(
        user_id=user.id,
        conversation_id=conversation_id,
    )
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.post("/hub/conversations/{conversation_id}/chat")
async def chat(
    conversation_id: str,
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to Jumbo and get a response."""
    _validate_uuid(conversation_id, "conversation_id")

    try:
        result = jumbo_hub.chat(
            user_id=user.id,
            conversation_id=conversation_id,
            message=req.message,
        )
        return result
    except LookupError:
        raise HTTPException(404, "Conversation not found")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        logger.warning("chat failed conv=%s: %s", conversation_id, exc)
        raise HTTPException(500, "Chat failed — please try again")


@router.patch("/hub/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Archive a conversation (soft delete)."""
    _validate_uuid(conversation_id, "conversation_id")

    updated = jumbo_hub.archive_conversation(
        user_id=user.id,
        conversation_id=conversation_id,
    )
    if not updated:
        raise HTTPException(404, "Conversation not found")
    return {"ok": True}


@router.post("/hub/save-note")
async def save_note(
    req: SaveNoteRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Save text as an agent_memory note."""
    _validate_uuid(req.brand_id, "brand_id")

    note_id = jumbo_hub.save_as_note(
        user_id=user.id,
        brand_id=req.brand_id,
        content=req.content,
        title=req.title,
    )
    if not note_id:
        raise HTTPException(500, "Failed to save note")
    return {"id": note_id}
