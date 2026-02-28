"""Notifications API: agent-generated notifications for the user."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.deps import get_admin_client
from app.auth import get_current_user
from app.schemas.notifications import NotificationOut, UnreadCount

logger = logging.getLogger("app.routers.notifications")

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationOut])
async def list_notifications(
    status: Optional[str] = Query(None, pattern=r"^(unread|read|dismissed|actioned)$"),
    notification_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """List notifications, newest first."""
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    q = (
        sb.table("agent_notifications")
        .select("*")
        .eq("user_id", user.id)
        .or_(f"scheduled_for.is.null,scheduled_for.lte.{now}")
    )
    if status:
        q = q.eq("status", status)
    if notification_type:
        q = q.eq("notification_type", notification_type)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(user=Depends(get_current_user)):
    """Get count of unread notifications, broken down by priority."""
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    resp = (
        sb.table("agent_notifications")
        .select("priority")
        .eq("user_id", user.id)
        .eq("status", "unread")
        .or_(f"scheduled_for.is.null,scheduled_for.lte.{now}")
        .execute()
    )
    items = resp.data or []
    by_priority: dict[str, int] = {}
    for item in items:
        p = item.get("priority", "medium")
        by_priority[p] = by_priority.get(p, 0) + 1
    return UnreadCount(count=len(items), by_priority=by_priority)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    """Mark a notification as read."""
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    resp = (
        sb.table("agent_notifications")
        .update({"status": "read", "read_at": now})
        .eq("id", notification_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.patch("/{notification_id}/dismiss")
async def dismiss_notification(notification_id: str, user=Depends(get_current_user)):
    """Dismiss a notification."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_notifications")
        .update({"status": "dismissed"})
        .eq("id", notification_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    """Mark all unread notifications as read."""
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    sb.table("agent_notifications").update(
        {"status": "read", "read_at": now}
    ).eq("user_id", user.id).eq("status", "unread").execute()
    return {"ok": True}


@router.get("/briefing/latest", response_model=Optional[NotificationOut])
async def latest_briefing(user=Depends(get_current_user)):
    """Get the most recent daily briefing."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_notifications")
        .select("*")
        .eq("user_id", user.id)
        .eq("notification_type", "briefing")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return resp.data[0]
