"""Goals API: CRUD for agent goals that drive autonomous behavior."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.deps import get_admin_client
from app.auth import get_current_user
from app.schemas.goals import GoalCreate, GoalOut, GoalUpdate

logger = logging.getLogger("app.routers.goals")

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=List[GoalOut])
async def list_goals(
    status: Optional[str] = Query(None, pattern=r"^(active|paused|completed|archived)$"),
    brand_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List goals, optionally filtered by status or brand."""
    sb = get_admin_client()
    q = sb.table("agent_goals").select("*").eq("user_id", user.id)
    if status:
        q = q.eq("status", status)
    if brand_id:
        q = q.eq("brand_id", brand_id)
    resp = q.order("created_at", desc=True).execute()
    return resp.data or []


@router.post("", response_model=GoalOut)
async def create_goal(body: GoalCreate, user=Depends(get_current_user)):
    """Create a new goal for agents to track."""
    sb = get_admin_client()
    row = {
        "user_id": user.id,
        "title": body.title,
        "description": body.description,
        "goal_type": body.goal_type,
        "target_value": body.target_value,
        "target_unit": body.target_unit,
        "platform": body.platform,
        "brand_id": body.brand_id,
        "priority": body.priority,
        "deadline_at": body.deadline_at.isoformat() if body.deadline_at else None,
    }
    resp = sb.table("agent_goals").insert(row).execute()
    if not resp.data:
        raise HTTPException(500, "Failed to create goal")
    return resp.data[0]


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(goal_id: str, user=Depends(get_current_user)):
    """Get a single goal."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_goals")
        .select("*")
        .eq("id", goal_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Goal not found")
    return resp.data[0]


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(goal_id: str, body: GoalUpdate, user=Depends(get_current_user)):
    """Update a goal."""
    sb = get_admin_client()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "deadline_at" in updates and updates["deadline_at"]:
        updates["deadline_at"] = updates["deadline_at"].isoformat()
    resp = (
        sb.table("agent_goals")
        .update(updates)
        .eq("id", goal_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Goal not found")
    return resp.data[0]


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, user=Depends(get_current_user)):
    """Delete a goal."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_goals")
        .delete()
        .eq("id", goal_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Goal not found")
    return {"ok": True}


@router.post("/{goal_id}/evaluate")
async def evaluate_goal(goal_id: str, user=Depends(get_current_user)):
    """Manually trigger evaluation of a single goal."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_goals")
        .select("*")
        .eq("id", goal_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Goal not found")

    goal = resp.data[0]
    from app.services.agent_orchestrator import evaluate_single_goal
    result = evaluate_single_goal(user.id, goal, sb)

    return {"goal_id": goal_id, "current_value": result.get("current_value", 0), "on_track": result.get("on_track", False)}
