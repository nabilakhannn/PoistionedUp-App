"""Pipeline Settings Router — Slice 90-A.

Lets users control the automated pipeline schedule from the app UI.

User endpoints (JWT auth):
  GET  /pipeline/settings          — get current settings
  PUT  /pipeline/settings          — update interval, enabled, run_now
  POST /pipeline/run-now           — trigger immediate run

VPS endpoint (pipeline key):
  GET  /orchestrator/pipeline/control  — VPS polls this before each run
  POST /orchestrator/pipeline/control/ack  — VPS calls after run to update last/next run times
"""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.pipeline_settings")

router = APIRouter(tags=["pipeline-settings"])

# ── Pipeline key auth (reused from pipeline.py pattern) ───────────────────


def _require_pipeline_key(
    x_pipeline_key: str = Header(..., alias="X-Pipeline-Key"),
) -> None:
    if not settings.pipeline_secret_key:
        raise HTTPException(503, "Pipeline key not configured.")
    if not hmac.compare_digest(x_pipeline_key, settings.pipeline_secret_key):
        raise HTTPException(401, "Invalid pipeline key")


# ── Helpers ────────────────────────────────────────────────────────────────


def _get_or_create_settings(user_id: str) -> dict:
    """Return the pipeline_settings row, creating defaults if missing."""
    sb = get_admin_client()
    result = (
        sb.table("pipeline_settings")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]

    # First time — create default row
    now = datetime.now(timezone.utc)
    default_next = now + timedelta(hours=24)
    row = {
        "user_id": user_id,
        "enabled": True,
        "interval_hours": 24,
        "run_now": False,
        "next_run_at": default_next.isoformat(),
    }
    created = sb.table("pipeline_settings").insert(row).execute()
    return created.data[0] if created.data else row


# ── Schemas ────────────────────────────────────────────────────────────────


class PipelineSettingsResponse(BaseModel):
    enabled: bool
    interval_hours: int
    run_now: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    monthly_budget_usd: float = 20.0


class UpdateSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = Field(None, ge=1, le=168)  # 1h – 1 week


class PipelineControlResponse(BaseModel):
    """Returned to VPS runner so it knows what to do."""
    enabled: bool
    run_now: bool
    interval_hours: int
    user_id: str


# ── User endpoints (JWT) ───────────────────────────────────────────────────


@router.get("/pipeline/settings", response_model=PipelineSettingsResponse)
async def get_pipeline_settings(user: CurrentUser = Depends(get_current_user)):
    """Get the current pipeline schedule settings for the logged-in user."""
    row = _get_or_create_settings(user.id)
    return PipelineSettingsResponse(
        enabled=row.get("enabled", True),
        interval_hours=row.get("interval_hours", 24),
        run_now=row.get("run_now", False),
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        monthly_budget_usd=float(row.get("monthly_budget_usd") or 20.0),
    )


@router.put("/pipeline/settings", response_model=PipelineSettingsResponse)
async def update_pipeline_settings(
    body: UpdateSettingsRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Update pipeline interval or toggle it on/off."""
    _get_or_create_settings(user.id)  # ensure row exists

    updates: dict = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.interval_hours is not None:
        updates["interval_hours"] = body.interval_hours
        # Recalculate next_run_at based on new interval
        now = datetime.now(timezone.utc)
        updates["next_run_at"] = (now + timedelta(hours=body.interval_hours)).isoformat()

    if not updates:
        raise HTTPException(400, "No fields to update")

    sb = get_admin_client()
    result = (
        sb.table("pipeline_settings")
        .update(updates)
        .eq("user_id", user.id)
        .execute()
    )
    row = result.data[0] if result.data else _get_or_create_settings(user.id)
    return PipelineSettingsResponse(
        enabled=row.get("enabled", True),
        interval_hours=row.get("interval_hours", 24),
        run_now=row.get("run_now", False),
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        monthly_budget_usd=float(row.get("monthly_budget_usd") or 20.0),
    )


@router.get("/pipeline/approvals/count")
async def get_approvals_count(user: CurrentUser = Depends(get_current_user)):
    """Return count of agent deliverables waiting for approval (status='review').

    Used by the NavBar to show the Approvals badge on Today without
    polling the full deliverables list.
    """
    try:
        sb = get_admin_client()
        result = (
            sb.table("agent_deliverables")
            .select("id", count="exact")
            .eq("user_id", user.id)
            .eq("status", "review")
            .execute()
        )
        return {"count": result.count or 0}
    except Exception as exc:
        logger.warning("get_approvals_count failed for user=%s: %s", user.id, exc)
        return {"count": 0}


@router.post("/pipeline/run-now", response_model=PipelineSettingsResponse)
async def trigger_run_now(user: CurrentUser = Depends(get_current_user)):
    """Flag the pipeline to run on the next VPS poll cycle (within ~1 min)."""
    _get_or_create_settings(user.id)

    sb = get_admin_client()
    result = (
        sb.table("pipeline_settings")
        .update({"run_now": True})
        .eq("user_id", user.id)
        .execute()
    )
    row = result.data[0] if result.data else {}
    return PipelineSettingsResponse(
        enabled=row.get("enabled", True),
        interval_hours=row.get("interval_hours", 24),
        run_now=True,
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
        monthly_budget_usd=float(row.get("monthly_budget_usd") or 20.0),
    )


# ── VPS runner endpoints (pipeline key) ───────────────────────────────────


@router.get("/orchestrator/pipeline/control")
async def get_all_pipeline_controls(
    _key: None = Depends(_require_pipeline_key),
):
    """Return pipeline settings for ALL users — VPS polls this before each cycle.

    Returns list of {user_id, enabled, run_now, interval_hours} so the runner
    knows which users to process and whether to force-run.
    """
    try:
        sb = get_admin_client()
        result = sb.table("pipeline_settings").select("*").execute()
        controls = [
            {
                "user_id": row["user_id"],
                "enabled": row.get("enabled", True),
                "run_now": row.get("run_now", False),
                "interval_hours": row.get("interval_hours", 24),
                "next_run_at": row.get("next_run_at"),
                "last_run_at": row.get("last_run_at"),
            }
            for row in (result.data or [])
        ]
        return {"controls": controls}
    except Exception as exc:
        logger.warning("get_all_pipeline_controls failed: %s", exc)
        return {"controls": []}


@router.post("/orchestrator/pipeline/control/ack")
async def ack_pipeline_run(
    request: Request,
    _key: None = Depends(_require_pipeline_key),
):
    """VPS calls this after completing a run to update last_run_at and next_run_at,
    and clear the run_now flag."""
    body = await request.json()
    user_id = body.get("user_id", "")
    interval_hours = int(body.get("interval_hours", 24))

    if not user_id:
        raise HTTPException(400, "user_id required")

    now = datetime.now(timezone.utc)
    next_run = now + timedelta(hours=interval_hours)

    try:
        sb = get_admin_client()
        sb.table("pipeline_settings").update({
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat(),
            "run_now": False,
        }).eq("user_id", user_id).execute()
        return {"ok": True}
    except Exception as exc:
        logger.warning("ack_pipeline_run failed for user=%s: %s", user_id, exc)
        return {"ok": False}
