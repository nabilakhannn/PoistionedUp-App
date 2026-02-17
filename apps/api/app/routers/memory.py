"""Agent Memory endpoints: list, approve, dismiss, edit, synthesize, delete."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.schemas.memory import (
    AgentMemoryCreate,
    AgentMemoryDetail,
    AgentMemorySummary,
    AgentMemoryUpdate,
    MemoryApprovalAction,
    MemorySynthesisResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# ── Helpers ──────────────────────────────────────────────

def _row_to_summary(row: dict) -> AgentMemorySummary:
    """Convert a DB row to a summary response."""
    return AgentMemorySummary(
        id=row["id"],
        memory_type=row["memory_type"],
        content=row["content"],
        confidence=row["confidence"],
        status=row["status"],
        platform=row.get("platform"),
        category=row.get("category"),
        source=row.get("source"),
        last_used_at=row.get("last_used_at"),
        created_at=row["created_at"],
    )


def _row_to_detail(row: dict) -> AgentMemoryDetail:
    """Convert a DB row to a full detail response."""
    return AgentMemoryDetail(
        id=row["id"],
        memory_type=row["memory_type"],
        content=row["content"],
        confidence=row["confidence"],
        status=row["status"],
        platform=row.get("platform"),
        category=row.get("category"),
        source=row.get("source"),
        evidence=row.get("evidence", []),
        related_post_ids=row.get("related_post_ids", []),
        supersedes_id=row.get("supersedes_id"),
        last_used_at=row.get("last_used_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ── CRUD ─────────────────────────────────────────────────


@router.post("", response_model=AgentMemorySummary, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: AgentMemoryCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new agent memory."""
    from app.services.agent_memory import create_memory as svc_create

    row = svc_create(
        user_id=user.id,
        memory_type=body.memory_type,
        content=body.content,
        confidence=body.confidence,
        platform=body.platform,
        category=body.category,
        source=body.source,
        related_post_ids=body.related_post_ids,
        status=body.status,
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory",
        )

    return _row_to_summary(row)


@router.get("", response_model=List[AgentMemorySummary])
async def list_memories(
    memory_type: Optional[str] = Query(None),
    memory_status: Optional[str] = Query(None, alias="status"),
    platform: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List agent memories with optional filters."""
    from app.services.agent_memory import list_memories as svc_list

    rows = svc_list(
        user_id=user.id,
        memory_type=memory_type,
        status=memory_status,
        platform=platform,
    )

    return [_row_to_summary(r) for r in rows]


@router.get("/pending", response_model=List[AgentMemorySummary])
async def list_pending_memories(
    user: CurrentUser = Depends(get_current_user),
):
    """List memories pending user approval (lessons)."""
    from app.services.agent_memory import list_memories as svc_list

    rows = svc_list(user_id=user.id, status="pending_approval")
    return [_row_to_summary(r) for r in rows]


@router.get("/{memory_id}", response_model=AgentMemoryDetail)
async def get_memory(
    memory_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get full detail for a memory."""
    from app.services.agent_memory import get_memory_by_id

    row = get_memory_by_id(memory_id, user.id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return _row_to_detail(row)


@router.patch("/{memory_id}", response_model=AgentMemorySummary)
async def update_memory(
    memory_id: str,
    body: AgentMemoryUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update a memory's content or metadata."""
    from app.services.agent_memory import update_memory as svc_update, get_memory_by_id

    # Verify memory exists
    existing = get_memory_by_id(memory_id, user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )

    updates = {}
    if body.content is not None:
        updates["content"] = body.content
    if body.confidence is not None:
        updates["confidence"] = body.confidence
    if body.platform is not None:
        updates["platform"] = body.platform
    if body.category is not None:
        updates["category"] = body.category

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    row = svc_update(memory_id, user.id, updates)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory",
        )

    return _row_to_summary(row)


@router.post("/{memory_id}/approve", response_model=AgentMemorySummary)
async def approve_memory(
    memory_id: str,
    body: Optional[MemoryApprovalAction] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Approve or dismiss a pending memory."""
    from app.services.agent_memory import (
        approve_memory as svc_approve,
        dismiss_memory as svc_dismiss,
        get_memory_by_id,
    )

    existing = get_memory_by_id(memory_id, user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )

    action = body.action if body else "approve"
    edited_content = body.edited_content if body else None

    if action == "dismiss":
        row = svc_dismiss(memory_id, user.id)
    else:
        row = svc_approve(memory_id, user.id, edited_content=edited_content)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval",
        )

    return _row_to_summary(row)


@router.post("/synthesize", response_model=MemorySynthesisResponse)
async def synthesize_memories(
    user: CurrentUser = Depends(get_current_user),
):
    """Consolidate observations into strategic lessons.

    Groups similar observations, detects patterns, and creates new
    'lesson' memories (pending approval). Old observations get superseded.
    """
    from app.services.agent_memory import synthesize_memories as svc_synth

    try:
        result = svc_synth(user.id)
    except Exception as e:
        logger.error("Memory synthesis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Synthesis failed. Please try again.",
        )

    return MemorySynthesisResponse(**result)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a memory permanently."""
    from app.services.agent_memory import delete_memory as svc_delete

    deleted = svc_delete(memory_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
