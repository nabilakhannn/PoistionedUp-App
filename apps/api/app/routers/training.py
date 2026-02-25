"""Agent Training API Router.

Two groups of endpoints:

Admin endpoints (prefix: /admin/training):
  - Manage prompt configs (system prompt sections)
  - Manage training examples (few-shot learning)
  - Review user feedback
  - View training statistics

User endpoints (prefix: /training):
  - Submit feedback on AI responses
  - Manage custom instructions per brand

All endpoints require authentication. Admin endpoints require
the service role (enforced at DB level via RLS).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.training import (
    CustomInstructionsOut,
    CustomInstructionsUpsert,
    FeedbackCreate,
    FeedbackOut,
    FeedbackSummary,
    PromptConfigOut,
    PromptConfigUpdate,
    TrainingExampleCreate,
    TrainingExampleOut,
    TrainingExampleUpdate,
    TrainingStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["training"])


# ════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS: Prompt Config
# ════════════════════════════════════════════════════════════════


@router.get("/admin/training/config", response_model=List[PromptConfigOut])
async def list_prompt_configs(
    config_type: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List all active prompt configurations."""
    sb = get_admin_client()
    query = (
        sb.table("agent_training_config")
        .select("*")
        .eq("is_active", True)
        .order("config_type")
        .order("config_key")
    )
    if config_type:
        query = query.eq("config_type", config_type)

    resp = query.execute()
    return resp.data or []


@router.get(
    "/admin/training/config/{config_key}",
    response_model=PromptConfigOut,
)
async def get_prompt_config(
    config_key: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single prompt config by key."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_training_config")
        .select("*")
        .eq("config_key", config_key)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Config not found")
    return resp.data[0]


@router.put(
    "/admin/training/config/{config_key}",
    response_model=PromptConfigOut,
)
async def update_prompt_config(
    config_key: str,
    body: PromptConfigUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update a prompt config section.

    Creates a new version: deactivates the old one and inserts a new row.
    This preserves version history.
    """
    sb = get_admin_client()

    # Get current version
    current = (
        sb.table("agent_training_config")
        .select("*")
        .eq("config_key", config_key)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Config not found")

    old_row = current.data[0]
    new_version = old_row.get("version", 1) + 1

    # Deactivate old version
    sb.table("agent_training_config").update({
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", old_row["id"]).execute()

    # Insert new version
    new_data = {
        "config_type": old_row["config_type"],
        "config_key": config_key,
        "content": body.content,
        "version": new_version,
        "is_active": True,
        "metadata": body.metadata or old_row.get("metadata", {}),
        "created_by": user.id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    insert_resp = (
        sb.table("agent_training_config")
        .insert(new_data)
        .execute()
    )

    logger.info(
        "Updated prompt config %s to version %d by %s",
        config_key, new_version, user.id,
    )
    return insert_resp.data[0] if insert_resp.data else new_data


@router.get(
    "/admin/training/config/{config_key}/history",
    response_model=List[PromptConfigOut],
)
async def get_config_history(
    config_key: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get version history for a prompt config."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_training_config")
        .select("*")
        .eq("config_key", config_key)
        .order("version", desc=True)
        .limit(20)
        .execute()
    )
    return resp.data or []


# ════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS: Training Examples
# ════════════════════════════════════════════════════════════════


@router.get(
    "/admin/training/examples",
    response_model=List[TrainingExampleOut],
)
async def list_training_examples(
    category: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List active training examples with optional filters."""
    sb = get_admin_client()
    query = (
        sb.table("agent_training_examples")
        .select("*")
        .eq("is_active", True)
        .order("created_at", desc=True)
    )
    if category:
        query = query.eq("category", category)
    if module:
        query = query.eq("module", module)

    resp = query.execute()
    return resp.data or []


@router.post(
    "/admin/training/examples",
    response_model=TrainingExampleOut,
    status_code=201,
)
async def create_training_example(
    body: TrainingExampleCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new training example."""
    sb = get_admin_client()
    data = body.model_dump()
    data["created_by"] = user.id
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    resp = sb.table("agent_training_examples").insert(data).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create example")

    logger.info("Created training example (category=%s) by %s", body.category, user.id)
    return resp.data[0]


@router.put(
    "/admin/training/examples/{example_id}",
    response_model=TrainingExampleOut,
)
async def update_training_example(
    example_id: str,
    body: TrainingExampleUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update an existing training example."""
    sb = get_admin_client()

    update_data = {
        k: v for k, v in body.model_dump().items() if v is not None
    }
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    resp = (
        sb.table("agent_training_examples")
        .update(update_data)
        .eq("id", example_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Example not found")

    logger.info("Updated training example %s by %s", example_id, user.id)
    return resp.data[0]


@router.delete("/admin/training/examples/{example_id}")
async def delete_training_example(
    example_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Soft-delete a training example (set is_active=false)."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_training_examples")
        .update({
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", example_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Example not found")

    logger.info("Deleted training example %s by %s", example_id, user.id)
    return {"status": "deleted", "id": example_id}


# ════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS: Feedback Review + Stats
# ════════════════════════════════════════════════════════════════


@router.get("/admin/training/feedback", response_model=List[FeedbackOut])
async def list_all_feedback(
    feedback_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    """List user feedback (admin view across all users)."""
    sb = get_admin_client()
    query = (
        sb.table("agent_feedback")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if feedback_type:
        query = query.eq("feedback_type", feedback_type)

    resp = query.execute()
    return resp.data or []


@router.get("/admin/training/stats", response_model=TrainingStats)
async def get_training_stats(
    user: CurrentUser = Depends(get_current_user),
):
    """Get overall training system statistics."""
    sb = get_admin_client()

    # Count configs
    configs = (
        sb.table("agent_training_config")
        .select("id", count="exact")
        .eq("is_active", True)
        .execute()
    )

    # Count examples
    examples = (
        sb.table("agent_training_examples")
        .select("id", count="exact")
        .eq("is_active", True)
        .execute()
    )

    # Count feedback
    feedback = (
        sb.table("agent_feedback")
        .select("feedback_type")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    feedback_data = feedback.data or []

    # Aggregate feedback by type
    by_type = {}
    for row in feedback_data:
        ft = row.get("feedback_type", "unknown")
        by_type[ft] = by_type.get(ft, 0) + 1

    # Recent corrections
    corrections = (
        sb.table("agent_feedback")
        .select("*")
        .eq("feedback_type", "correction")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    return TrainingStats(
        total_configs=len(configs.data or []),
        total_examples=len(examples.data or []),
        total_feedback=len(feedback_data),
        feedback_by_type=by_type,
        recent_corrections=corrections.data or [],
    )


# ════════════════════════════════════════════════════════════════
# USER ENDPOINTS: Feedback
# ════════════════════════════════════════════════════════════════


@router.post("/training/feedback", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit feedback on an AI response."""
    sb = get_admin_client()

    data = body.model_dump()
    data["user_id"] = user.id
    data["response_metadata"] = data.get("response_metadata") or {}

    resp = sb.table("agent_feedback").insert(data).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    logger.info(
        "Feedback submitted: type=%s user=%s brand=%s",
        body.feedback_type, user.id, body.brand_id,
    )
    return resp.data[0]


@router.get(
    "/training/feedback/history",
    response_model=List[FeedbackOut],
)
async def get_my_feedback(
    brand_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Get the current user's feedback history."""
    sb = get_admin_client()
    query = (
        sb.table("agent_feedback")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    return resp.data or []


@router.get(
    "/training/feedback/summary",
    response_model=FeedbackSummary,
)
async def get_feedback_summary(
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Get a summary of the current user's feedback."""
    sb = get_admin_client()
    query = (
        sb.table("agent_feedback")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(100)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    data = resp.data or []

    summary = FeedbackSummary(
        total_feedback=len(data),
        thumbs_up=sum(1 for r in data if r.get("feedback_type") == "thumbs_up"),
        thumbs_down=sum(1 for r in data if r.get("feedback_type") == "thumbs_down"),
        corrections=sum(1 for r in data if r.get("feedback_type") == "correction"),
        voice_mismatches=sum(1 for r in data if r.get("feedback_type") == "voice_mismatch"),
        recent_feedback=data[:10],
    )
    return summary


# ════════════════════════════════════════════════════════════════
# USER ENDPOINTS: Custom Instructions
# ════════════════════════════════════════════════════════════════


@router.get(
    "/training/instructions/{brand_id}",
    response_model=Optional[CustomInstructionsOut],
)
async def get_custom_instructions(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get custom instructions for a brand."""
    sb = get_admin_client()
    resp = (
        sb.table("agent_custom_instructions")
        .select("*")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return resp.data[0]


@router.put(
    "/training/instructions/{brand_id}",
    response_model=CustomInstructionsOut,
)
async def upsert_custom_instructions(
    brand_id: str,
    body: CustomInstructionsUpsert,
    user: CurrentUser = Depends(get_current_user),
):
    """Create or update custom instructions for a brand.

    Uses upsert on (user_id, brand_id) unique constraint.
    """
    sb = get_admin_client()

    # Check if instructions exist
    existing = (
        sb.table("agent_custom_instructions")
        .select("id")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .limit(1)
        .execute()
    )

    data = body.model_dump()
    data["user_id"] = user.id
    data["brand_id"] = brand_id
    data["is_active"] = True
    data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if existing.data:
        # Update
        resp = (
            sb.table("agent_custom_instructions")
            .update(data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        # Insert
        resp = (
            sb.table("agent_custom_instructions")
            .insert(data)
            .execute()
        )

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to save instructions")

    logger.info("Saved custom instructions for user=%s brand=%s", user.id, brand_id)
    return resp.data[0]
