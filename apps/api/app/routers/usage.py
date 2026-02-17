"""Usage & cost tracking endpoints.

Provides:
  - GET /usage          -- Summary of costs (total, per-workflow, daily/weekly/monthly)
  - GET /usage/daily    -- Daily breakdown for charting
  - GET /usage/cap      -- Current daily workflow cap status

Also exposes helper functions for rate limiting in other routers.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/usage", tags=["usage"])


# ── Response schemas ─────────────────────────────────────────


class WorkflowCostSummary(BaseModel):
    workflow_id: str
    goal_text: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    step_count: int
    created_at: Optional[str] = None


class DailyUsage(BaseModel):
    date: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    call_count: int


class UsageSummary(BaseModel):
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    total_calls: int
    workflow_count: int
    daily_workflows_used: int
    daily_workflow_cap: int
    period_costs: Dict[str, float]  # daily, weekly, monthly
    workflows: List[WorkflowCostSummary]


class CapStatus(BaseModel):
    daily_workflows_used: int
    daily_workflow_cap: int
    remaining: int
    at_limit: bool


# ── Helpers ──────────────────────────────────────────────────


def check_daily_workflow_cap(user_id: str) -> Dict[str, Any]:
    """Check if user has hit their daily workflow cap.

    Returns dict with used, cap, remaining, and at_limit.
    Called by workflow creation endpoint for rate limiting.
    """
    admin = get_admin_client()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    resp = (
        admin.table("workflows")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", today_start.isoformat())
        .execute()
    )

    used = resp.count if resp.count is not None else len(resp.data or [])
    cap = settings.max_workflows_per_user_per_day

    return {
        "used": used,
        "cap": cap,
        "remaining": max(0, cap - used),
        "at_limit": used >= cap,
    }


# ── Endpoints ────────────────────────────────────────────────


@router.get("", response_model=UsageSummary)
async def get_usage_summary(user: CurrentUser = Depends(get_current_user)):
    """Get comprehensive usage summary for the current user."""
    admin = get_admin_client()

    # Get all usage cost rows for this user
    costs_resp = (
        admin.table("usage_costs")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    costs = costs_resp.data or []

    # Totals
    total_cost = sum(float(c.get("estimated_cost", 0)) for c in costs)
    total_input = sum(c.get("input_tokens", 0) for c in costs)
    total_output = sum(c.get("output_tokens", 0) for c in costs)
    total_calls = len(costs)

    # Period-based costs
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    daily_cost = 0.0
    weekly_cost = 0.0
    monthly_cost = 0.0

    for c in costs:
        created = c.get("created_at", "")
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        cost_val = float(c.get("estimated_cost", 0))
        if ts >= today_start:
            daily_cost += cost_val
        if ts >= week_start:
            weekly_cost += cost_val
        if ts >= month_start:
            monthly_cost += cost_val

    # Per-workflow breakdown
    wf_costs = {}  # type: Dict[str, Dict[str, Any]]
    for c in costs:
        wf_id = c.get("workflow_id", "unknown")
        if wf_id not in wf_costs:
            wf_costs[wf_id] = {
                "workflow_id": wf_id,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "step_count": 0,
            }
        wf_costs[wf_id]["total_cost"] += float(c.get("estimated_cost", 0))
        wf_costs[wf_id]["total_input_tokens"] += c.get("input_tokens", 0)
        wf_costs[wf_id]["total_output_tokens"] += c.get("output_tokens", 0)
        wf_costs[wf_id]["step_count"] += 1

    # Enrich workflow summaries with goal_text
    wf_ids = list(wf_costs.keys())
    workflows_info = {}  # type: Dict[str, Dict[str, Any]]
    if wf_ids:
        wf_resp = (
            admin.table("workflows")
            .select("id, goal_text, created_at")
            .eq("user_id", user.id)
            .in_("id", wf_ids)
            .execute()
        )
        for wf in (wf_resp.data or []):
            workflows_info[wf["id"]] = wf

    workflow_summaries = []
    for wf_id, data in wf_costs.items():
        info = workflows_info.get(wf_id, {})
        workflow_summaries.append(
            WorkflowCostSummary(
                workflow_id=wf_id,
                goal_text=info.get("goal_text", "Unknown workflow"),
                total_cost=round(data["total_cost"], 6),
                total_input_tokens=data["total_input_tokens"],
                total_output_tokens=data["total_output_tokens"],
                step_count=data["step_count"],
                created_at=info.get("created_at"),
            )
        )

    # Sort by cost descending
    workflow_summaries.sort(key=lambda x: x.total_cost, reverse=True)

    # Daily cap status
    cap_info = check_daily_workflow_cap(user.id)

    return UsageSummary(
        total_cost=round(total_cost, 6),
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_calls=total_calls,
        workflow_count=len(wf_costs),
        daily_workflows_used=cap_info["used"],
        daily_workflow_cap=cap_info["cap"],
        period_costs={
            "daily": round(daily_cost, 6),
            "weekly": round(weekly_cost, 6),
            "monthly": round(monthly_cost, 6),
        },
        workflows=workflow_summaries,
    )


@router.get("/daily", response_model=List[DailyUsage])
async def get_daily_usage(
    days: int = 30,
    user: CurrentUser = Depends(get_current_user),
):
    """Get daily usage breakdown for the last N days (for charting)."""
    admin = get_admin_client()

    since = datetime.now(timezone.utc) - timedelta(days=days)

    costs_resp = (
        admin.table("usage_costs")
        .select("*")
        .eq("user_id", user.id)
        .gte("created_at", since.isoformat())
        .order("created_at")
        .execute()
    )
    costs = costs_resp.data or []

    # Group by date
    daily = {}  # type: Dict[str, Dict[str, Any]]
    for c in costs:
        created = c.get("created_at", "")
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            date_str = ts.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue

        if date_str not in daily:
            daily[date_str] = {
                "date": date_str,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "call_count": 0,
            }
        daily[date_str]["total_cost"] += float(c.get("estimated_cost", 0))
        daily[date_str]["total_input_tokens"] += c.get("input_tokens", 0)
        daily[date_str]["total_output_tokens"] += c.get("output_tokens", 0)
        daily[date_str]["call_count"] += 1

    # Fill in missing days with zeros
    result = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime(
            "%Y-%m-%d"
        )
        if d in daily:
            result.append(
                DailyUsage(
                    date=d,
                    total_cost=round(daily[d]["total_cost"], 6),
                    total_input_tokens=daily[d]["total_input_tokens"],
                    total_output_tokens=daily[d]["total_output_tokens"],
                    call_count=daily[d]["call_count"],
                )
            )
        else:
            result.append(
                DailyUsage(
                    date=d,
                    total_cost=0.0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    call_count=0,
                )
            )

    return result


@router.get("/cap", response_model=CapStatus)
async def get_cap_status(user: CurrentUser = Depends(get_current_user)):
    """Get the current daily workflow cap status."""
    cap_info = check_daily_workflow_cap(user.id)
    return CapStatus(
        daily_workflows_used=cap_info["used"],
        daily_workflow_cap=cap_info["cap"],
        remaining=cap_info["remaining"],
        at_limit=cap_info["at_limit"],
    )
