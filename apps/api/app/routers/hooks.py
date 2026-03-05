"""Hook Library API — Slice 102 (Fix F).

User-visible, editable hook library. Agents pull from this before writing content.
Auto-populated when user approves a post (opening line saved as hook).
"""

from __future__ import annotations

import logging
import re
import uuid as _uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.hooks")
router = APIRouter(prefix="/hooks", tags=["hooks"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_HOOK_TYPES = frozenset(
    ["anxiety", "benefit", "story", "competitor", "belief", "curiosity", "custom"]
)


def _valid_uuid(val: str) -> bool:
    return bool(_UUID_RE.match(val))


class HookCreate(BaseModel):
    brand_id: Optional[str] = None
    hook_text: str
    hook_type: str = "custom"
    source: str = "manual"
    engagement_score: Optional[float] = None


class HookUpdate(BaseModel):
    hook_text: Optional[str] = None
    hook_type: Optional[str] = None
    engagement_score: Optional[float] = None


# ── List ─────────────────────────────────────────────────────────


@router.get("")
async def list_hooks(
    brand_id: Optional[str] = Query(None),
    hook_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    """List all hooks for the user, optionally filtered by brand_id or type."""
    if brand_id and not _valid_uuid(brand_id):
        raise HTTPException(400, "Invalid brand_id format")

    sb = get_admin_client()
    q = (
        sb.table("hook_library")
        .select("*")
        .eq("user_id", user.id)
    )
    if brand_id:
        q = q.eq("brand_id", brand_id)
    if hook_type:
        if hook_type not in VALID_HOOK_TYPES:
            raise HTTPException(400, f"Invalid hook_type. Valid: {sorted(VALID_HOOK_TYPES)}")
        q = q.eq("hook_type", hook_type)

    result = q.order("times_used", desc=True).order("created_at", desc=True).limit(limit).execute()
    return result.data or []


# ── Create ───────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_hook(
    body: HookCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new hook. Users can add their own hooks to guide agents."""
    if body.brand_id and not _valid_uuid(body.brand_id):
        raise HTTPException(400, "Invalid brand_id format")

    hook_text = body.hook_text.strip()
    if not hook_text:
        raise HTTPException(400, "hook_text cannot be empty")
    if len(hook_text) > 1000:
        raise HTTPException(400, "hook_text cannot exceed 1000 characters")

    hook_type = body.hook_type.lower()
    if hook_type not in VALID_HOOK_TYPES:
        raise HTTPException(400, f"Invalid hook_type. Valid: {sorted(VALID_HOOK_TYPES)}")

    sb = get_admin_client()

    # IDOR guard: verify brand belongs to user
    if body.brand_id:
        brand_check = (
            sb.table("personal_brands")
            .select("id")
            .eq("id", body.brand_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if not brand_check.data:
            raise HTTPException(403, "Brand not found or access denied")

    row = {
        "id": str(_uuid.uuid4()),
        "user_id": user.id,
        "brand_id": body.brand_id,
        "hook_text": hook_text,
        "hook_type": hook_type,
        "source": body.source or "manual",
        "engagement_score": body.engagement_score,
        "times_used": 0,
    }
    result = sb.table("hook_library").insert(row).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create hook")
    return result.data[0]


# ── Update ───────────────────────────────────────────────────────


@router.patch("/{hook_id}")
async def update_hook(
    hook_id: str,
    body: HookUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update hook text, type, or engagement score."""
    if not _valid_uuid(hook_id):
        raise HTTPException(400, "Invalid hook_id format")

    updates: dict = {}
    if body.hook_text is not None:
        text = body.hook_text.strip()
        if not text:
            raise HTTPException(400, "hook_text cannot be empty")
        updates["hook_text"] = text[:1000]
    if body.hook_type is not None:
        ht = body.hook_type.lower()
        if ht not in VALID_HOOK_TYPES:
            raise HTTPException(400, f"Invalid hook_type. Valid: {sorted(VALID_HOOK_TYPES)}")
        updates["hook_type"] = ht
    if body.engagement_score is not None:
        updates["engagement_score"] = body.engagement_score

    if not updates:
        raise HTTPException(400, "No fields to update")

    sb = get_admin_client()
    result = (
        sb.table("hook_library")
        .update(updates)
        .eq("id", hook_id)
        .eq("user_id", user.id)  # IDOR guard
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Hook not found or access denied")
    return result.data[0]


# ── Delete ───────────────────────────────────────────────────────


@router.delete("/{hook_id}", status_code=204)
async def delete_hook(
    hook_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a hook from the library."""
    if not _valid_uuid(hook_id):
        raise HTTPException(400, "Invalid hook_id format")

    sb = get_admin_client()
    result = (
        sb.table("hook_library")
        .delete()
        .eq("id", hook_id)
        .eq("user_id", user.id)  # IDOR guard
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Hook not found or access denied")


# ── Get hooks for agent use (also available via agent bridge) ────


@router.get("/for-agent")
async def get_hooks_for_agent(
    brand_id: str = Query(..., description="Brand ID"),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Get hooks formatted for agent prompt injection.

    Returns hooks grouped by type, formatted as a writing guide.
    Agents call this before each copywriting task.
    """
    if not _valid_uuid(brand_id):
        raise HTTPException(400, "Invalid brand_id format")

    sb = get_admin_client()

    # IDOR: verify brand belongs to user
    brand_check = (
        sb.table("personal_brands")
        .select("id")
        .eq("id", brand_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not brand_check.data:
        raise HTTPException(403, "Brand not found or access denied")

    result = (
        sb.table("hook_library")
        .select("hook_text, hook_type, times_used, engagement_score")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .order("times_used", desc=True)
        .limit(limit)
        .execute()
    )
    hooks = result.data or []

    # Group by type
    grouped: dict = {}
    for h in hooks:
        t = h.get("hook_type", "custom")
        grouped.setdefault(t, [])
        grouped[t].append(h["hook_text"])

    # Format as prompt-injectable text
    lines = ["## Hook Library — Use These As Writing Examples\n"]
    for htype, texts in grouped.items():
        lines.append(f"\n### {htype.title()} Hooks")
        for text in texts[:5]:
            lines.append(f"- {text}")

    return {
        "hooks": hooks,
        "formatted": "\n".join(lines) if len(hooks) > 0 else "",
        "total": len(hooks),
    }
