"""Marketplace Router — Slice 109.

Agent Marketplace workflow registry, execution, and history endpoints.
Separate from existing workflows.py (content pipeline workflows).
"""

from __future__ import annotations

import re
import uuid as _uuid_mod
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_SLUG = re.compile(r"^[a-z0-9\-]{2,60}$")


# ── Request / Response schemas ─────────────────────────────────────

class WorkflowRunRequest(BaseModel):
    brand_id: str
    inputs: dict = Field(default_factory=dict)
    engine: str = "builtin"
    step_index: Optional[int] = None
    previous_outputs: Optional[list] = None


class WorkflowRunResponse(BaseModel):
    run_id: str
    status: str
    content: Optional[str] = None
    error: Optional[str] = None
    engine: str = "builtin"
    duration_ms: int = 0
    tokens_used: int = 0
    model_used: str = ""


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/registry")
async def get_registry(user: CurrentUser = Depends(get_current_user)):
    """Return the full workflow registry + seed framework docs on first call."""
    from app.services.workflow_engine import get_registry, seed_system_frameworks

    # Seed system frameworks idempotently
    await seed_system_frameworks()

    return get_registry()


@router.post("/run/{slug}", response_model=WorkflowRunResponse)
async def run_workflow(
    slug: str,
    body: WorkflowRunRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Execute a marketplace workflow. Returns result synchronously for built-in engine."""
    if not _SLUG.match(slug):
        raise HTTPException(status_code=400, detail="Invalid workflow slug")
    if not _UUID.match(body.brand_id):
        raise HTTPException(status_code=400, detail="Invalid brand_id")

    from app.services.workflow_engine import execute_workflow

    result = await execute_workflow(
        workflow_slug=slug,
        inputs=body.inputs,
        brand_id=body.brand_id,
        user_id=user.id,
        engine=body.engine,
        step_index=body.step_index,
        previous_outputs=body.previous_outputs,
    )

    return WorkflowRunResponse(
        run_id=result.get("run_id", ""),
        status=result.get("status", "failed"),
        content=result.get("content"),
        error=result.get("error"),
        engine=result.get("engine", "builtin"),
        duration_ms=result.get("duration_ms", 0),
        tokens_used=result.get("tokens_used", 0),
        model_used=result.get("model_used", ""),
    )


@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get the status of a workflow run."""
    if not _UUID.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id")

    from app.services.workflow_engine import get_workflow_run

    run = await get_workflow_run(run_id, user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/history")
async def get_history(
    brand_id: str = Query(...),
    workflow_slug: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    """Get workflow run history for a brand."""
    if not _UUID.match(brand_id):
        raise HTTPException(status_code=400, detail="Invalid brand_id")

    from app.services.workflow_engine import get_workflow_history

    runs = await get_workflow_history(
        user_id=user.id,
        brand_id=brand_id,
        workflow_slug=workflow_slug,
        limit=limit,
        offset=offset,
    )
    return {"runs": runs, "total": len(runs)}


@router.post("/runs/{run_id}/save-to-inbox")
async def save_run_to_inbox(
    run_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Save a completed workflow run to the agent_deliverables approval inbox.

    A01 IDOR: verifies workflow_runs.user_id == auth user before creating deliverable.
    Idempotent: if deliverable_id already set on the run, returns existing deliverable.
    """
    if not _UUID.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id")

    sb = get_admin_client()

    # Fetch the run — enforces IDOR via user_id
    run_result = sb.table("workflow_runs").select("*").eq("id", run_id).eq("user_id", user.id).execute()
    if not run_result.data:
        raise HTTPException(status_code=404, detail="Run not found")

    run = run_result.data[0]

    # Idempotency: already saved
    if run.get("deliverable_id"):
        deliverable = sb.table("agent_deliverables").select("*").eq("id", run["deliverable_id"]).execute()
        if deliverable.data:
            return {"deliverable_id": run["deliverable_id"], "already_saved": True}

    content = run.get("output") or ""
    if not content.strip():
        raise HTTPException(status_code=422, detail="Run has no output to save")

    # Build title from workflow slug
    slug = run.get("workflow_slug", "workflow")
    title = slug.replace("-", " ").title() + " — Workflow Output"

    deliverable_id = str(_uuid_mod.uuid4())
    row: dict = {
        "id": deliverable_id,
        "user_id": user.id,
        "title": title[:200],
        "content": content[:100_000],
        "deliverable_type": "content",
        "created_by_agent_id": "marketplace",
        "status": "review",
        "source": "marketplace",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if run.get("brand_id"):
        row["brand_id"] = run["brand_id"]

    sb.table("agent_deliverables").insert(row).execute()

    # Link back from run → deliverable
    sb.table("workflow_runs").update({"deliverable_id": deliverable_id}).eq("id", run_id).execute()

    return {"deliverable_id": deliverable_id, "already_saved": False}
