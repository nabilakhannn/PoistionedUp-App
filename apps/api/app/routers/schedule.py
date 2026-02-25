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
from app.services.analytics import track_event

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
    brand_id: Optional[str] = None


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
    brand_id: Optional[str] = None
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
async def get_kanban_board(
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Get all scheduled items grouped by kanban column."""
    admin = get_admin_client()

    query = (
        admin.table("scheduled_items")
        .select("*")
        .eq("user_id", user.id)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = (
        query
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
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Get scheduled items within a date range for calendar view."""
    admin = get_admin_client()

    query = (
        admin.table("scheduled_items")
        .select("*")
        .eq("user_id", user.id)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = (
        query
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

    if body.brand_id:
        insert_data["brand_id"] = body.brand_id

    if body.scheduled_at:
        insert_data["scheduled_at"] = body.scheduled_at
        if body.status == "draft":
            insert_data["status"] = "scheduled"

    if body.workflow_id:
        insert_data["workflow_id"] = body.workflow_id
    if body.asset_id:
        insert_data["asset_id"] = body.asset_id

    resp = admin.table("scheduled_items").insert(insert_data).execute()
    item = resp.data[0]

    track_event(user.id, "schedule_item_created", {
        "item_id": item["id"],
        "platform": body.platform,
        "content_type": body.content_type,
        "status": item.get("status", "draft"),
        "brand_id": body.brand_id or "",
    })

    return item


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

    track_event(user.id, "schedule_import", {
        "workflow_id": workflow_id,
        "items_imported": len(resp.data or []),
    })

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

    track_event(user.id, "schedule_item_updated", {
        "item_id": item_id,
        "fields_updated": list(update_data.keys()),
    })

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

    track_event(user.id, "schedule_item_moved", {
        "item_id": item_id,
        "old_status": existing.data[0]["status"],
        "new_status": body.status,
        "new_position": body.column_order,
    })

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

    track_event(user.id, "schedule_item_deleted", {"item_id": item_id})


# ── Auto-schedule from research ─────────────────────────────


# Map research idea formats → schedule content_type
_FORMAT_MAP = {
    "video": "youtube_long",
    "carousel": "linkedin_post",
    "post": "linkedin_post",
    "thread": "twitter_post",
    "story": "short_form",
    "reel": "short_form",
    "short": "youtube_short",
}

# Map research idea platforms → schedule platform
_PLATFORM_MAP = {
    "youtube": "youtube",
    "linkedin": "linkedin",
    "twitter": "twitter",
    "x": "twitter",
    "tiktok": "tiktok",
    "instagram": "instagram",
}


class AutoScheduleRequest(BaseModel):
    schedule_dates: bool = Field(
        False, description="Whether to auto-assign dates based on the week-1 calendar"
    )


@router.post("/from-research/{session_id}")
async def auto_schedule_from_research(
    session_id: str,
    body: AutoScheduleRequest = AutoScheduleRequest(),
    user: CurrentUser = Depends(get_current_user),
):
    """Create draft schedule items from a completed research session's content ideas.

    Pulls content_ideas and content_calendar_week_1 from the research session
    results and converts each into a scheduled item in "draft" status.
    """
    admin = get_admin_client()

    # 1. Fetch the research session
    sess_resp = (
        admin.table("brand_research_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not sess_resp.data:
        raise HTTPException(status_code=404, detail="Research session not found")

    session = sess_resp.data[0]
    results = session.get("results", {})
    brand_id = session.get("brand_id")

    # 2. Extract content ideas
    ideas_data = results.get("content_ideas", {})
    content_ideas = ideas_data.get("content_ideas", [])
    calendar_week_1 = ideas_data.get("content_calendar_week_1", [])

    if not content_ideas:
        raise HTTPException(
            status_code=422,
            detail="No content ideas found in this research session. Run the content_ideas stage first.",
        )

    # 3. Build day → date map for week-1 calendar scheduling
    day_dates: Dict[str, str] = {}
    if body.schedule_dates and calendar_week_1:
        from datetime import timedelta

        # Start from next Monday
        today = datetime.now(timezone.utc).date()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        next_monday = today + timedelta(days=days_until_monday)

        day_offsets = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        for entry in calendar_week_1:
            day_name = (entry.get("day") or "").strip().lower()
            offset = day_offsets.get(day_name)
            if offset is not None:
                sched_date = next_monday + timedelta(days=offset)
                # Schedule at 9am UTC
                day_dates[entry.get("title", "")] = datetime(
                    sched_date.year, sched_date.month, sched_date.day,
                    9, 0, 0, tzinfo=timezone.utc,
                ).isoformat()

    # 4. Convert each idea → scheduled item
    items_to_insert = []
    strategy_data = results.get("content_strategy", {})

    for i, idea in enumerate(content_ideas[:20]):  # Cap at 20
        title = (idea.get("title") or f"Research Idea {i+1}")[:500]
        fmt = (idea.get("format") or "post").strip().lower()
        raw_platform = (idea.get("platform") or "other").strip().lower()

        content_type = _FORMAT_MAP.get(fmt, "note")
        platform = _PLATFORM_MAP.get(raw_platform, "other")

        # Refine content_type based on platform when format is generic
        if fmt == "video" and platform == "tiktok":
            content_type = "short_form"
        elif fmt == "video" and platform == "youtube":
            content_type = "youtube_long"
        elif fmt == "post" and platform == "twitter":
            content_type = "twitter_post"

        item = {
            "user_id": user.id,
            "title": title,
            "platform": platform,
            "content_type": content_type,
            "body_preview": (idea.get("hook") or idea.get("brief") or "")[:200],
            "content_json": {
                "research_idea": idea,
                "pillar": idea.get("pillar"),
                "research_session_id": session_id,
                "source": "auto_research",
            },
            "status": "draft",
            "column_order": i,
            "color_label": "purple",
            "notes": f"Auto-generated from research | Pillar: {idea.get('pillar', 'N/A')} | Engagement: {idea.get('estimated_engagement', 'N/A')}",
        }

        if brand_id:
            item["brand_id"] = brand_id

        # Match against week-1 calendar for date scheduling
        if body.schedule_dates and title in day_dates:
            item["scheduled_at"] = day_dates[title]
            item["status"] = "scheduled"

        items_to_insert.append(item)

    if not items_to_insert:
        raise HTTPException(status_code=422, detail="Could not convert any research ideas to schedule items.")

    # 5. Batch insert
    resp = admin.table("scheduled_items").insert(items_to_insert).execute()
    created = resp.data or []

    track_event(user.id, "schedule_from_research", {
        "session_id": session_id,
        "brand_id": brand_id or "",
        "items_created": len(created),
        "dates_scheduled": body.schedule_dates,
    })

    return {
        "created": len(created),
        "items": created,
        "message": f"Created {len(created)} content ideas as draft schedule items.",
    }
