"""Publishing router — Slice 86.

Endpoints to trigger immediate or batch publishing of scheduled content
to social platforms using the user's stored connector credentials.

Routes:
    POST /schedule/{item_id}/publish        — Publish one item immediately
    POST /schedule/run-due                  — Run all due scheduled items
    GET  /schedule/{item_id}/publish-status — Check publish status + error
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

router = APIRouter(tags=["publishing"])


class PublishResponse(BaseModel):
    success: bool
    item_id: str
    platform: str
    published_url: Optional[str] = None
    published_at: Optional[str] = None
    error: Optional[str] = None


class RunDueResponse(BaseModel):
    published: int
    failed: int
    skipped: int
    errors: List


class PublishStatusResponse(BaseModel):
    item_id: str
    status: str
    published_url: Optional[str] = None
    published_at: Optional[str] = None
    publish_error: Optional[str] = None
    publish_attempted_at: Optional[str] = None


@router.post("/schedule/{item_id}/publish", response_model=PublishResponse)
async def publish_now(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Publish a single scheduled_item immediately.

    Uses the user's stored connector credentials for the item's platform.
    Returns the live post URL on success, or an error message on failure.
    """
    from app.services.publishing import publish_item

    user_id = user.id
    sb = get_admin_client()

    result = publish_item(item_id=item_id, user_id=user_id, sb=sb)

    if not result.success and result.error == "Item not found or access denied":
        raise HTTPException(status_code=404, detail="Item not found or access denied")

    return PublishResponse(
        success=result.success,
        item_id=result.item_id,
        platform=result.platform,
        published_url=result.published_url,
        published_at=result.published_at,
        error=result.error,
    )


@router.post("/schedule/run-due", response_model=RunDueResponse)
async def run_due_posts(
    user: CurrentUser = Depends(get_current_user),
):
    """Run all scheduled items whose scheduled_at time has passed.

    Processes up to 50 due items per call (safety cap).
    Failed items keep their 'scheduled' status and will retry on next call.
    """
    from app.services.publishing import run_due_posts as _run_due

    user_id = user.id
    sb = get_admin_client()

    result = _run_due(user_id=user_id, sb=sb)

    return RunDueResponse(
        published=result.published,
        failed=result.failed,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.get("/schedule/{item_id}/publish-status", response_model=PublishStatusResponse)
async def get_publish_status(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get the current publish status, URL, and error for a scheduled item."""
    user_id = user.id
    sb = get_admin_client()

    resp = (
        sb.table("scheduled_items")
        .select("id, status, published_url, published_at, publish_error, publish_attempted_at")
        .eq("id", item_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")

    row = resp.data[0]
    return PublishStatusResponse(
        item_id=row["id"],
        status=row["status"],
        published_url=row.get("published_url"),
        published_at=row.get("published_at"),
        publish_error=row.get("publish_error"),
        publish_attempted_at=row.get("publish_attempted_at"),
    )
