"""Marketplace Router — Slice 109.

Agent Marketplace workflow registry, execution, and history endpoints.
Separate from existing workflows.py (content pipeline workflows).
"""

from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user

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
