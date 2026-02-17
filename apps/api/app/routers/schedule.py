"""Schedule endpoints: kanban board + calendar for content planning.

Provides:
  - GET  /schedule              -- All items grouped by kanban column
  - GET  /schedule/calendar     -- Items with scheduled_at in a date range
  - POST /schedule              -- Create a new scheduled item (or import from workflow)
  - POST /schedule/import/{workflow_id} -- Import approved content from a workflow
  - PATCH /schedule/{id}        -- Update item (move columns, reschedule, edit)
  - PATCH /schedule/{id}/move   -- Move item to a different column + position
  - DELETE /schedule/{id}       -- Delete item
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["schedule"])

VALID_STATUSES = ["draft", "scheduled", "published", "archived"]
VALID_PLATFORMS = ["youtube", "linkedin", "twitter", "tiktok", "instagram", "other"]
VALID_COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "pink", None]


# ── Schemas ──────────────────────────────────────────────────


class ScheduledItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    platform: str = "other"
    content_type: str = "note"
    body_preview: Optional[str] = None
    content_json: Dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    scheduled_at: Optional[str] = None
    color_label: Optional[str] = None
    notes: Optional[str] = None
    workflow_id: Optional[str] = None
    asset_id: Optional[str] = None


class ScheduledItemUpdate(BaseModel):
    title: Optional[str] = None
    platform: Optional[str] = None
    content_type: Optional[str] = None
    body_preview: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    published_url: Optional[str] = None
    color_label: Optional[str] = None
    notes: Optional[str] = None
    column_order: Optional[int] = None


class MoveRequest(BaseModel):
    status: str
    column_order: int = 0


class ScheduledItem(BaseModel):
    id: str
    user_id: str
    title: str
    platform: str
    content_type: str
    body_preview: Optional[str] = None
    content_json: Dict[str, Any] = Field(default_factory=dict)
    workflow_id: Optional[str] = None
    asset_id: Optional[str] = None
    content_post_id: Optional[str] = None
    status: str
    column_order: int
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    published_url: Optional[str] = None
    color_label: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class KanbanBoard(BaseModel):
    draft: List[ScheduledItem]
    scheduled: List[ScheduledItem]
    published: List[ScheduledItem]
    archived: List[ScheduledItem]


# ── Endpoints ────────────────────────────────────────────────


@router.get("", response_model=KanbanBoard)
async def get_kanban_board(user: CurrentUser = Depends(get_current_user)):
    """Get all scheduled items grouped by kanban column."""
    admin = get_admin_client()

    resp = (
        admin.table("scheduled_items")
        .select("*")
        .eq("user_id", user.id)
        .order("column_order")
        .order("created_at", desc=True)
        .execute()
    )

    board = {"draft": [], "scheduled": [], "published": [], "archived": []}
    for row in (resp.data or []):
        col = row.get("status", "draft")
        if col in board:
            board[col].append(row)

    return board


@router.get("/calendar")
async def get_calendar_items(
    start: str = Query(..., description="Start date (ISO format)"),
    end: str = Query(..., description="End date (ISO format)"),
    user: CurrentUser = Depends(get_current_user),
):
    """Get scheduled items within a date range for calendar view."""
    admin = get_admin_client()

    resp = (
        admin.table("scheduled_items")
        .select("*")
        .eq("user_id", user.id)
        .not_.is_("scheduled_at", "null")
        .gte("scheduled_at", start)
        .lte("scheduled_at", end)
        .order("scheduled_at")
        .execute()
    )

    return resp.data or []


@router.post("", response_model=ScheduledItem, status_code=status.HTTP_201_CREATED)
async def create_scheduled_item(
    body: ScheduledItemCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new scheduled item."""
    admin = get_admin_client()

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {body.status}. Valid: {VALID_STATUSES}",
        )

    # Get next column_order for the target status
    existing = (
        admin.table("scheduled_items")
        .select("column_order")
        .eq("user_id", user.id)
        .eq("status", body.status or "draft")
        .order("column_order", desc=True)
        .limit(1)
        .execute()
    )
    next_order = (existing.data[0]["column_order"] + 1) if existing.data else 0

    insert_data = {
        "user_id": user.id,
        "title": body.title,
        "platform": body.platform,
        "content_type": body.content_type,
        "body_preview": body.body_preview,
        "content_json": body.content_json,
        "status": body.status or "draft",
        "column_order": next_order,
        "color_label": body.color_label,
        "notes": body.notes,
    }

    if body.scheduled_at:
        insert_data["scheduled_at"] = body.scheduled_at
        if body.status == "draft":
            insert_data["status"] = "scheduled"

    if body.workflow_id:
        insert_data["workflow_id"] = body.workflow_id
    if body.asset_id:
        insert_data["asset_id"] = body.asset_id

    resp = admin.table("scheduled_items").insert(insert_data).execute()
    return resp.data[0]


@router.post("/import/{workflow_id}")
async def import_from_workflow(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Import all approved content from a workflow into the schedule as draft items."""
    admin = get_admin_client()

    # Verify workflow ownership
    wf_resp = (
        admin.table("workflows")
        .select("id, goal_text, settings, status")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = wf_resp.data[0]
    settings = wf.get("settings", {})
    platforms = settings.get("platforms", ["youtube"])

    # Get the content pack from snapshots
    snap_resp = (
        admin.table("workflow_snapshots")
        .select("state_json")
        .eq("workflow_id", workflow_id)
        .in_("step_id", ["editor", "testing", "approval"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    pack = {}
    if snap_resp.data:
        state = snap_resp.data[0].get("state_json", {})
        pack = state.get("edited_pack") or state.get("content_pack", {})

    if not pack:
        pack = settings.get("_edited_pack") or settings.get("_content_pack", {})

    # Create scheduled items from the content pack
    items_created = []
    goal = wf.get("goal_text", "Imported content")

    # YouTube long-form
    yt_long = pack.get("youtube_long", {})
    if yt_long and "youtube" in platforms:
        hook = yt_long.get("hook", "")
        items_created.append({
            "user_id": user.id,
            "title": (pack.get("titles", [goal]) or [goal])[0],
            "platform": "youtube",
            "content_type": "youtube_long",
            "body_preview": hook[:200] if hook else goal[:200],
            "content_json": {"youtube_long": yt_long, "titles": pack.get("titles", []), "description": pack.get("description", ""), "tags": pack.get("tags", [])},
            "workflow_id": workflow_id,
            "status": "draft",
            "column_order": 0,
        })

    # YouTube shorts
    for i, short in enumerate(pack.get("youtube_shorts", [])):
        if "youtube" in platforms:
            items_created.append({
                "user_id": user.id,
                "title": f"Short: {short.get('hook', goal)[:80]}",
                "platform": "youtube",
                "content_type": "youtube_short",
                "body_preview": short.get("script", "")[:200],
                "content_json": short,
                "workflow_id": workflow_id,
                "status": "draft",
                "column_order": i + 1,
            })

    # LinkedIn posts
    for i, post in enumerate(pack.get("linkedin_posts", [])):
        if "linkedin" in platforms:
            items_created.append({
                "user_id": user.id,
                "title": f"LinkedIn: {post.get('hook_line', goal)[:80]}",
                "platform": "linkedin",
                "content_type": "linkedin_post",
                "body_preview": post.get("body", "")[:200],
                "content_json": post,
                "workflow_id": workflow_id,
                "status": "draft",
                "column_order": i,
            })

    # Twitter posts
    for i, tweet in enumerate(pack.get("twitter_posts", [])):
        if "twitter" in platforms:
            items_created.append({
                "user_id": user.id,
                "title": f"Tweet: {tweet.get('tweet_text', goal)[:80]}",
                "platform": "twitter",
                "content_type": "twitter_post",
                "body_preview": tweet.get("tweet_text", "")[:200],
                "content_json": tweet,
                "workflow_id": workflow_id,
                "status": "draft",
                "column_order": i,
            })

    # Short-form scripts
    for i, script in enumerate(pack.get("short_form_scripts", [])):
        if "short_form" in platforms or "tiktok" in platforms:
            items_created.append({
                "user_id": user.id,
                "title": f"Short-form: {script.get('hook', goal)[:80]}",
                "platform": "tiktok",
                "content_type": "short_form",
                "body_preview": script.get("script", "")[:200],
                "content_json": script,
                "workflow_id": workflow_id,
                "status": "draft",
                "column_order": i,
            })

    if not items_created:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No content found in this workflow to import.",
        )

    resp = admin.table("scheduled_items").insert(items_created).execute()
    return {
        "imported": len(resp.data or []),
        "items": resp.data or [],
        "message": f"Imported {len(resp.data or [])} items from workflow into your schedule.",
    }


@router.patch("/{item_id}", response_model=ScheduledItem)
async def update_scheduled_item(
    item_id: str,
    body: ScheduledItemUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update a scheduled item (edit title, reschedule, change status, etc.)."""
    admin = get_admin_client()

    # Verify ownership
    existing = (
        admin.table("scheduled_items")
        .select("id")
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = {}
    for field in ["title", "platform", "content_type", "body_preview",
                   "content_json", "status", "scheduled_at", "published_at",
                   "published_url", "color_label", "notes", "column_order"]:
        val = getattr(body, field, None)
        if val is not None:
            update_data[field] = val

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {body.status}. Valid: {VALID_STATUSES}",
        )

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    resp = (
        admin.table("scheduled_items")
        .update(update_data)
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    return resp.data[0]


@router.patch("/{item_id}/move", response_model=ScheduledItem)
async def move_item(
    item_id: str,
    body: MoveRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Move an item to a different kanban column and position (drag-and-drop)."""
    admin = get_admin_client()

    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {body.status}. Valid: {VALID_STATUSES}",
        )

    # Verify ownership
    existing = (
        admin.table("scheduled_items")
        .select("id, status")
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = {
        "status": body.status,
        "column_order": body.column_order,
    }

    # Auto-set published_at when moving to published
    if body.status == "published" and existing.data[0]["status"] != "published":
        update_data["published_at"] = datetime.now(timezone.utc).isoformat()

    resp = (
        admin.table("scheduled_items")
        .update(update_data)
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    return resp.data[0]


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_item(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a scheduled item."""
    admin = get_admin_client()

    resp = (
        admin.table("scheduled_items")
        .delete()
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")
