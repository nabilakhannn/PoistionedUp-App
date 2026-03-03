"""Bulk Ad Creative router.

Endpoints:
  - POST /brands/{brand_id}/ad-creative/generate  -- Generate 40+ ad variations from research
  - POST /brands/{brand_id}/ad-creative/{deliverable_id}/stage  -- Stage approved ads to Composer
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.services.ad_creative import (
    ALL_HOOK_TYPES,
    ALL_PLATFORMS,
    DEFAULT_COUNT_PER_HOOK,
    generate_bulk_ads,
    stage_approved_ads,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands", tags=["ad-creative"])


# ── Schemas ──────────────────────────────────────────────────


class AdGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Completed brand research session ID")
    hook_types: Optional[List[str]] = Field(
        default=None,
        description="Hook types to generate. Defaults to all 5.",
    )
    platforms: Optional[List[str]] = Field(
        default=None,
        description="Target platforms. Defaults to facebook, instagram, linkedin.",
    )
    count_per_hook: int = Field(
        default=DEFAULT_COUNT_PER_HOOK,
        ge=1,
        le=12,
        description="Variations to generate per hook type (1-12).",
    )


class AdGenerateResponse(BaseModel):
    deliverable_id: str
    total_count: int
    variations_by_hook: dict
    hook_errors: dict = {}
    brand_name: str
    niche: str


class AdStageRequest(BaseModel):
    variation_ids: List[str] = Field(..., description="IDs of approved variations to stage")


class AdStageResponse(BaseModel):
    staged_count: int
    scheduled_item_ids: List[str]


# ── Endpoints ────────────────────────────────────────────────


@router.post("/{brand_id}/ad-creative/generate", response_model=AdGenerateResponse)
async def generate_ads(
    brand_id: str,
    body: AdGenerateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate bulk ad variations from a completed brand research session.

    Makes 5 focused LLM calls (one per hook type) and produces 8 variations
    each = 40 total. Results are saved to agent_deliverables for review.
    """
    # Validate hook types
    if body.hook_types:
        invalid = [h for h in body.hook_types if h not in ALL_HOOK_TYPES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid hook types: {invalid}. Valid: {ALL_HOOK_TYPES}",
            )

    # Validate platforms
    if body.platforms:
        invalid_p = [p for p in body.platforms if p not in ALL_PLATFORMS]
        if invalid_p:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid platforms: {invalid_p}. Valid: {ALL_PLATFORMS}",
            )

    try:
        result = generate_bulk_ads(
            user_id=user.id,
            brand_id=brand_id,
            session_id=body.session_id,
            hook_types=body.hook_types,
            platforms=body.platforms,
            count_per_hook=body.count_per_hook,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Ad generation failed for brand=%s: %s", brand_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ad generation failed. Please try again.",
        )

    return AdGenerateResponse(**result)


@router.post("/{brand_id}/ad-creative/{deliverable_id}/stage", response_model=AdStageResponse)
async def stage_ads(
    brand_id: str,
    deliverable_id: str,
    body: AdStageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Stage approved ad variations as draft scheduled items in the Composer.

    Each approved variation_id creates one draft scheduled_item with
    content_type=ad_copy for review and scheduling.
    """
    if not body.variation_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="variation_ids cannot be empty",
        )

    try:
        result = stage_approved_ads(
            user_id=user.id,
            brand_id=brand_id,
            deliverable_id=deliverable_id,
            variation_ids=body.variation_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Ad staging failed for deliverable=%s: %s", deliverable_id, e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Staging failed. Please try again.",
        )

    return AdStageResponse(**result)


# ── Approval Persistence ─────────────────────────────────────


class AdApprovalRequest(BaseModel):
    approved_ids: List[str] = Field(default_factory=list, description="Variation IDs the user has approved")
    dismissed_ids: List[str] = Field(default_factory=list, description="Variation IDs the user has dismissed")


@router.patch("/{brand_id}/ad-creative/{deliverable_id}/approvals")
async def update_approvals(
    brand_id: str,
    deliverable_id: str,
    body: AdApprovalRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Persist approval/dismissal state for ad variations.

    Called on every toggle so approval selections survive page reloads,
    browser crashes, and cross-device access. Overwrites the full set each time
    (client sends the complete current state, not a diff).
    """
    from app.deps import get_admin_client
    from datetime import datetime, timezone

    sb = get_admin_client()

    # Verify deliverable ownership before update
    check = (
        sb.table("agent_deliverables")
        .select("id")
        .eq("id", deliverable_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deliverable not found")

    sb.table("agent_deliverables").update({
        "approved_variation_ids": body.approved_ids,
        "dismissed_variation_ids": body.dismissed_ids,
        "approvals_updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", deliverable_id).eq("user_id", user.id).execute()

    return {
        "ok": True,
        "approved_count": len(body.approved_ids),
        "dismissed_count": len(body.dismissed_ids),
    }
