"""Experiment + Self-Voice DNA endpoints."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status

from app.auth import CurrentUser, get_current_user
from app.schemas.experiments import (
    ExperimentCreate,
    ExperimentDetail,
    ExperimentSummary,
    ExperimentUpdate,
    ExperimentActionResponse,
    SelfVoiceAnalysisResponse,
    SelfVoiceDNA,
    VoiceDriftResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["experiments"])


# ── Helpers ──────────────────────────────────────────────

def _row_to_summary(row: dict) -> ExperimentSummary:
    """Convert a DB row to a summary response."""
    return ExperimentSummary(
        id=row["id"],
        hypothesis=row["hypothesis"],
        variable=row["variable"],
        variant_a=row["variant_a"],
        variant_b=row["variant_b"],
        platform=row["platform"],
        status=row["status"],
        target_posts=row.get("target_posts", 4),
        variant_a_count=len(row.get("variant_a_posts", []) or []),
        variant_b_count=len(row.get("variant_b_posts", []) or []),
        variant_a_avg_engagement=row.get("variant_a_avg_engagement"),
        variant_b_avg_engagement=row.get("variant_b_avg_engagement"),
        winner=row.get("winner"),
        conclusion=row.get("conclusion"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def _row_to_detail(row: dict) -> ExperimentDetail:
    """Convert a DB row to a detail response."""
    return ExperimentDetail(
        id=row["id"],
        hypothesis=row["hypothesis"],
        variable=row["variable"],
        variant_a=row["variant_a"],
        variant_b=row["variant_b"],
        platform=row["platform"],
        status=row["status"],
        target_posts=row.get("target_posts", 4),
        variant_a_posts=[str(p) for p in (row.get("variant_a_posts", []) or [])],
        variant_b_posts=[str(p) for p in (row.get("variant_b_posts", []) or [])],
        variant_a_avg_engagement=row.get("variant_a_avg_engagement"),
        variant_b_avg_engagement=row.get("variant_b_avg_engagement"),
        winner=row.get("winner"),
        conclusion=row.get("conclusion"),
        resulting_memory_id=row.get("resulting_memory_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row.get("completed_at"),
    )


# ── Experiment Endpoints ─────────────────────────────────

@router.post("/experiments", response_model=ExperimentSummary, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: ExperimentCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new experiment (proposed by default)."""
    from app.services.experiments import create_experiment as svc_create
    try:
        row = svc_create(
            user_id=user.id,
            hypothesis=body.hypothesis,
            variable=body.variable,
            variant_a=body.variant_a,
            variant_b=body.variant_b,
            platform=body.platform,
            target_posts=body.target_posts,
        )
        return _row_to_summary(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments", response_model=List[ExperimentSummary])
async def list_experiments(
    status_filter: Optional[str] = Query(None, alias="status"),
    platform: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List experiments with optional filters."""
    from app.services.experiments import list_experiments as svc_list
    rows = svc_list(user.id, status=status_filter, platform=platform)
    return [_row_to_summary(r) for r in rows]


# Static routes BEFORE dynamic {experiment_id}

@router.post("/experiments/auto-propose", response_model=List[ExperimentSummary])
async def auto_propose(
    user: CurrentUser = Depends(get_current_user),
):
    """Auto-propose experiments based on performance data."""
    from app.services.experiments import auto_propose_experiments
    rows = auto_propose_experiments(user.id)
    return [_row_to_summary(r) for r in rows]


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get experiment detail."""
    from app.services.experiments import get_experiment_by_id
    row = get_experiment_by_id(user.id, experiment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _row_to_detail(row)


@router.patch("/experiments/{experiment_id}", response_model=ExperimentSummary)
async def update_experiment(
    experiment_id: str,
    body: ExperimentUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update experiment fields."""
    from app.services.experiments import update_experiment as svc_update, get_experiment_by_id
    exp = get_experiment_by_id(user.id, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    updates = body.dict(exclude_none=True)
    if not updates:
        return _row_to_summary(exp)

    row = svc_update(user.id, experiment_id, updates)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to update experiment")
    return _row_to_summary(row)


@router.post("/experiments/{experiment_id}/approve", response_model=ExperimentActionResponse)
async def approve_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Approve a proposed experiment."""
    from app.services.experiments import approve_experiment as svc_approve
    try:
        row = svc_approve(user.id, experiment_id)
        return ExperimentActionResponse(
            id=row["id"],
            status=row["status"],
            message=f"Experiment approved. Start assigning posts to variants.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/cancel", response_model=ExperimentActionResponse)
async def cancel_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel an experiment."""
    from app.services.experiments import cancel_experiment as svc_cancel
    try:
        row = svc_cancel(user.id, experiment_id)
        return ExperimentActionResponse(
            id=row["id"],
            status=row["status"],
            message="Experiment cancelled.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/assign", response_model=ExperimentActionResponse)
async def assign_post(
    experiment_id: str,
    post_id: str = Body(..., embed=True),
    variant: str = Body(..., embed=True),
    user: CurrentUser = Depends(get_current_user),
):
    """Assign a published post to an experiment variant."""
    from app.services.experiments import assign_post_to_experiment
    try:
        row = assign_post_to_experiment(user.id, experiment_id, post_id, variant)
        a_count = len(row.get("variant_a_posts", []) or [])
        b_count = len(row.get("variant_b_posts", []) or [])
        return ExperimentActionResponse(
            id=row["id"],
            status=row["status"],
            message=f"Post assigned to {variant}. A: {a_count} posts, B: {b_count} posts.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/conclude", response_model=ExperimentDetail)
async def conclude_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Evaluate experiment results and determine the winner."""
    from app.services.experiments import check_and_conclude
    try:
        row = check_and_conclude(user.id, experiment_id)
        return _row_to_detail(row)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/experiments/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete an experiment."""
    from app.services.experiments import delete_experiment as svc_delete
    if not svc_delete(user.id, experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")


# ── Self-Voice DNA Endpoints ─────────────────────────────

@router.post("/voice/analyze-self", response_model=SelfVoiceAnalysisResponse)
async def analyze_self_voice(
    user: CurrentUser = Depends(get_current_user),
):
    """Analyze the user's own published content to build their Voice DNA."""
    from app.services.self_voice import analyze_self_voice as svc_analyze
    try:
        voice_dna = svc_analyze(user.id)
        return SelfVoiceAnalysisResponse(
            voice_dna=SelfVoiceDNA(**voice_dna),
            message=f"Voice DNA extracted from {voice_dna.get('posts_analyzed', 0)} posts.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/voice/baseline", response_model=Optional[SelfVoiceDNA])
async def get_voice_baseline(
    user: CurrentUser = Depends(get_current_user),
):
    """Get the user's stored self-voice DNA."""
    from app.services.self_voice import get_voice_baseline as svc_baseline
    result = svc_baseline(user.id)
    if not result:
        return None
    return SelfVoiceDNA(**result)


@router.post("/voice/drift-check", response_model=VoiceDriftResult)
async def check_drift(
    text: str = Body(..., embed=True),
    user: CurrentUser = Depends(get_current_user),
):
    """Check how closely generated text matches the user's natural voice."""
    from app.services.self_voice import check_voice_drift
    result = check_voice_drift(user.id, text)
    return VoiceDriftResult(**result)
