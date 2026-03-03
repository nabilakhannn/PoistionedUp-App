"""Ledger router — Slice 85.

Read-only endpoints for the agent audit ledger.
Write operations are internal only (tool_use_agents.py).

Endpoints:
  GET  /ledger/runs/                    paginated list of agent runs
  GET  /ledger/runs/{run_id}/entries    all ledger entries for one run
  GET  /ledger/agents/{agent_id}/runs   filter runs by agent
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ledger", tags=["ledger"])


# ── GET /ledger/runs/ ─────────────────────────────────────────────

@router.get("/runs/")
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List sdk_agent_runs for this user, most recent first."""
    sb = get_admin_client()
    query = (
        sb.table("sdk_agent_runs")
        .select("id, agent_id, task_type, status, prompt_summary, result_summary, model_used, total_tokens, tool_calls_count, duration_ms, brand_id, created_at, completed_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data or []


# ── GET /ledger/runs/{run_id}/entries ─────────────────────────────

@router.get("/runs/{run_id}/entries")
async def get_run_entries(
    run_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get all ledger entries for a specific agent run, oldest first."""
    sb = get_admin_client()
    result = (
        sb.table("agent_ledger")
        .select("id, agent_id, action_type, action_description, tool_name, tool_input_summary, tool_result_summary, tokens_used, created_at")
        .eq("user_id", user.id)
        .eq("run_id", run_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


# ── GET /ledger/agents/{agent_id}/runs ───────────────────────────

@router.get("/agents/{agent_id}/runs")
async def get_agent_runs(
    agent_id: str,
    limit: int = Query(30, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Get recent runs for a specific agent."""
    sb = get_admin_client()
    result = (
        sb.table("sdk_agent_runs")
        .select("id, agent_id, task_type, status, total_tokens, tool_calls_count, duration_ms, created_at, completed_at")
        .eq("user_id", user.id)
        .eq("agent_id", agent_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ── GET /ledger/summary ───────────────────────────────────────────

@router.get("/summary")
async def get_ledger_summary(
    days: int = Query(7, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user),
):
    """Dashboard summary: runs today, avg tokens, tool calls total."""
    sb = get_admin_client()
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = (
        sb.table("sdk_agent_runs")
        .select("id, status, total_tokens, tool_calls_count, duration_ms, created_at")
        .eq("user_id", user.id)
        .gte("created_at", since)
        .execute()
    )
    rows = result.data or []
    total_runs = len(rows)
    completed = [r for r in rows if r["status"] == "completed"]
    failed = [r for r in rows if r["status"] == "failed"]
    total_tokens = sum(r.get("total_tokens") or 0 for r in rows)
    total_tool_calls = sum(r.get("tool_calls_count") or 0 for r in rows)
    avg_tokens = int(total_tokens / len(completed)) if completed else 0
    avg_duration_ms = int(
        sum(r.get("duration_ms") or 0 for r in completed) / len(completed)
    ) if completed else 0

    return {
        "days": days,
        "total_runs": total_runs,
        "completed": len(completed),
        "failed": len(failed),
        "total_tokens": total_tokens,
        "avg_tokens_per_run": avg_tokens,
        "total_tool_calls": total_tool_calls,
        "avg_duration_ms": avg_duration_ms,
    }
