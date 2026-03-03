"""Content Stages Router — Slice 90.

CRUD endpoints for the Notion-style editable Kanban pipeline stages.
Users can add, rename, reorder, and delete stages per brand.

Endpoints (all JWT-protected):
  GET    /stages               — list stages for a brand
  POST   /stages               — create a stage
  PATCH  /stages/{id}          — rename / update a stage
  DELETE /stages/{id}          — delete a stage
  PUT    /stages/reorder        — reorder stages (update positions)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.stages")

router = APIRouter(tags=["stages"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

DEFAULT_STAGES = [
    {"name": "Research", "color": "blue", "position": 0, "stage_type": "auto", "agent_id": "trend-analyzer", "is_default": True},
    {"name": "Writing", "color": "purple", "position": 1, "stage_type": "auto", "agent_id": "copywriter", "is_default": True},
    {"name": "QA Review", "color": "amber", "position": 2, "stage_type": "auto", "agent_id": "qa-reviewer", "is_default": True},
    {"name": "Your Review", "color": "orange", "position": 3, "stage_type": "manual", "agent_id": None, "is_default": True},
    {"name": "Published", "color": "green", "position": 4, "stage_type": "auto", "agent_id": "distributor", "is_default": True},
]


# ── Schemas ────────────────────────────────────────────────────────────────


class StageResponse(BaseModel):
    id: str
    brand_id: str
    name: str
    color: str
    position: int
    stage_type: str
    agent_id: Optional[str] = None
    is_default: bool
    created_at: str


class CreateStageRequest(BaseModel):
    brand_id: str
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="blue", max_length=50)
    stage_type: str = Field(default="manual")
    agent_id: Optional[str] = Field(default=None, max_length=100)


class UpdateStageRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    color: Optional[str] = Field(default=None, max_length=50)
    stage_type: Optional[str] = None
    agent_id: Optional[str] = Field(default=None, max_length=100)


class ReorderRequest(BaseModel):
    brand_id: str
    order: List[str]  # stage IDs in new position order


# ── Helpers ────────────────────────────────────────────────────────────────


def _ensure_defaults(user_id: str, brand_id: str, sb) -> None:
    """Seed default stages for a brand if none exist yet."""
    check = (
        sb.table("content_stages")
        .select("id", count="exact")
        .eq("brand_id", brand_id)
        .execute()
    )
    if check.count and check.count > 0:
        return

    rows = [
        {"user_id": user_id, "brand_id": brand_id, **stage}
        for stage in DEFAULT_STAGES
    ]
    sb.table("content_stages").insert(rows).execute()


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/stages", response_model=List[StageResponse])
async def list_stages(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """List all stages for a brand, ordered by position."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()
    _ensure_defaults(user.id, brand_id, sb)

    result = (
        sb.table("content_stages")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("user_id", user.id)
        .order("position")
        .execute()
    )
    return [
        StageResponse(
            id=row["id"],
            brand_id=row["brand_id"],
            name=row["name"],
            color=row.get("color", "blue"),
            position=row["position"],
            stage_type=row.get("stage_type", "manual"),
            agent_id=row.get("agent_id"),
            is_default=row.get("is_default", False),
            created_at=str(row.get("created_at", "")),
        )
        for row in (result.data or [])
    ]


@router.post("/stages", response_model=StageResponse, status_code=201)
async def create_stage(
    body: CreateStageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new stage for a brand."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()

    # Get current max position
    existing = (
        sb.table("content_stages")
        .select("position")
        .eq("brand_id", body.brand_id)
        .order("position", desc=True)
        .limit(1)
        .execute()
    )
    max_pos = existing.data[0]["position"] if existing.data else -1

    row = {
        "user_id": user.id,
        "brand_id": body.brand_id,
        "name": body.name,
        "color": body.color,
        "position": max_pos + 1,
        "stage_type": body.stage_type,
        "agent_id": body.agent_id,
        "is_default": False,
    }

    result = sb.table("content_stages").insert(row).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create stage")

    created = result.data[0]
    return StageResponse(
        id=created["id"],
        brand_id=created["brand_id"],
        name=created["name"],
        color=created.get("color", "blue"),
        position=created["position"],
        stage_type=created.get("stage_type", "manual"),
        agent_id=created.get("agent_id"),
        is_default=created.get("is_default", False),
        created_at=str(created.get("created_at", "")),
    )


@router.patch("/stages/{stage_id}", response_model=StageResponse)
async def update_stage(
    stage_id: str,
    body: UpdateStageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Rename or update a stage. Returns the updated stage."""
    if not _UUID_RE.match(stage_id):
        raise HTTPException(400, "Invalid stage_id")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    sb = get_admin_client()
    result = (
        sb.table("content_stages")
        .update(updates)
        .eq("id", stage_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Stage not found or not yours")

    updated = result.data[0]
    return StageResponse(
        id=updated["id"],
        brand_id=updated["brand_id"],
        name=updated["name"],
        color=updated.get("color", "blue"),
        position=updated["position"],
        stage_type=updated.get("stage_type", "manual"),
        agent_id=updated.get("agent_id"),
        is_default=updated.get("is_default", False),
        created_at=str(updated.get("created_at", "")),
    )


@router.delete("/stages/{stage_id}", status_code=204)
async def delete_stage(
    stage_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a stage. Cannot delete if only 1 stage remains."""
    if not _UUID_RE.match(stage_id):
        raise HTTPException(400, "Invalid stage_id")

    sb = get_admin_client()

    # Check stage exists and belongs to user
    check = (
        sb.table("content_stages")
        .select("brand_id")
        .eq("id", stage_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not check.data:
        raise HTTPException(404, "Stage not found or not yours")

    brand_id = check.data[0]["brand_id"]

    # Prevent deleting last stage
    count_result = (
        sb.table("content_stages")
        .select("id", count="exact")
        .eq("brand_id", brand_id)
        .execute()
    )
    if count_result.count and count_result.count <= 1:
        raise HTTPException(400, "Cannot delete the last stage")

    sb.table("content_stages").delete().eq("id", stage_id).eq("user_id", user.id).execute()
    return None


@router.put("/stages/reorder")
async def reorder_stages(
    body: ReorderRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Reorder stages — accepts list of stage IDs in new order."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()

    for idx, stage_id in enumerate(body.order):
        if not _UUID_RE.match(stage_id):
            continue
        sb.table("content_stages").update({"position": idx}).eq("id", stage_id).eq("user_id", user.id).execute()

    return {"ok": True, "reordered": len(body.order)}
