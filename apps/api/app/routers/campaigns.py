"""Campaigns Router — Slice 108.

CRUD + execution endpoints for the campaign system.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.campaigns")

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ── Schemas ──────────────────────────────────────────────────────────


class CampaignCreate(BaseModel):
    brand_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    platforms: list[str] = ["linkedin"]
    content_types: list[str] = ["text"]
    total_pieces: int = Field(default=5, ge=1, le=100)
    template_id: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    total_pieces: Optional[int] = None
    platforms: Optional[list[str]] = None
    content_types: Optional[list[str]] = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("")
async def list_campaigns(
    brand_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List all campaigns for the current user."""
    from app.services.campaigns import list_campaigns as _list
    return _list(user.id, brand_id)


@router.post("")
async def create_campaign(body: CampaignCreate, user: CurrentUser = Depends(get_current_user)):
    """Create a new campaign."""
    from app.services.campaigns import create_campaign as _create
    try:
        return _create(
            user_id=user.id,
            brand_id=body.brand_id,
            name=body.name,
            description=body.description,
            platforms=body.platforms,
            content_types=body.content_types,
            total_pieces=body.total_pieces,
            template_id=body.template_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Get a single campaign."""
    from app.services.campaigns import get_campaign as _get
    campaign = _get(user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}")
async def update_campaign(campaign_id: str, body: CampaignUpdate, user: CurrentUser = Depends(get_current_user)):
    """Update a campaign."""
    from app.services.campaigns import update_campaign as _update
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = _update(user.id, campaign_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Delete a campaign."""
    from app.services.campaigns import delete_campaign as _delete
    if not _delete(user.id, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted"}


@router.post("/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Move campaign from planning → active."""
    from app.services.campaigns import update_campaign as _update
    result = _update(user.id, campaign_id, {"status": "active"})
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Pause a campaign."""
    from app.services.campaigns import update_campaign as _update
    result = _update(user.id, campaign_id, {"status": "paused"})
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.post("/{campaign_id}/increment-completed")
async def increment_completed(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Increment completed count (called after content is generated)."""
    from app.services.campaigns import increment_completed as _inc
    result = _inc(user.id, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result


@router.post("/{campaign_id}/increment-approved")
async def increment_approved(campaign_id: str, user: CurrentUser = Depends(get_current_user)):
    """Increment approved count (called after content is approved)."""
    from app.services.campaigns import increment_approved as _inc
    result = _inc(user.id, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result
