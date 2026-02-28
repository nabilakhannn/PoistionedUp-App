"""Content Repurposing router.

Endpoints:
  - POST /repurpose       -- Repurpose content across platforms
  - GET  /repurpose/platforms -- List available target platforms
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.repurpose import (
    PlatformInfo,
    RepurposeRequest,
    RepurposeResponse,
    RepurposedItem,
    VALID_TARGET_PLATFORMS,
)
from app.services.analytics import track_event
from app.services.repurpose import _fetch_source_content, repurpose_content
from worker.graph.prompts.repurpose import PLATFORM_CONSTRAINTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repurpose", tags=["repurpose"])


@router.post("", response_model=RepurposeResponse)
async def repurpose(
    body: RepurposeRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Repurpose content from one platform to multiple target platforms."""
    admin = get_admin_client()

    # Resolve source text
    source_text = body.source_text
    if body.source_id and not source_text:
        source_text = _fetch_source_content(body.source_id, user.id, admin)
        if not source_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source content not found. Check the source_id or provide source_text.",
            )

    if not source_text or not source_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No source content provided. Supply either source_id or source_text.",
        )

    # Run repurposing
    items = repurpose_content(
        user_id=user.id,
        source_text=source_text,
        source_platform=body.source_platform,
        target_platforms=body.target_platforms,
        brand_id=body.brand_id,
        sb=admin,
    )

    # Optionally create schedule items
    scheduled_count = 0
    if body.auto_schedule and items:
        schedule_items = []
        for i, item in enumerate(items):
            if not item.get("body"):
                continue
            schedule_items.append({
                "user_id": user.id,
                "title": item["title"][:500],
                "platform": item["platform"],
                "content_type": item["content_type"],
                "body_preview": item["body"][:200],
                "content_json": {
                    "body": item["body"],
                    "metadata": item.get("metadata", {}),
                    "source": "repurpose",
                    "source_platform": body.source_platform,
                },
                "status": "draft",
                "column_order": i,
                "color_label": "blue",
                "notes": f"Repurposed from {body.source_platform}",
            })
            if body.brand_id:
                schedule_items[-1]["brand_id"] = body.brand_id

        if schedule_items:
            resp = admin.table("scheduled_items").insert(schedule_items).execute()
            scheduled_count = len(resp.data or [])

    track_event(user.id, "content_repurposed", {
        "source_platform": body.source_platform,
        "target_platforms": body.target_platforms,
        "items_created": len(items),
        "auto_scheduled": scheduled_count,
        "brand_id": body.brand_id or "",
    })

    return RepurposeResponse(
        source_platform=body.source_platform,
        repurposed=[RepurposedItem(**item) for item in items],
        scheduled_items_created=scheduled_count,
    )


@router.get("/platforms", response_model=List[PlatformInfo])
async def list_platforms(
    user: CurrentUser = Depends(get_current_user),
):
    """List available target platforms with their constraints."""
    platforms = []
    for name in sorted(VALID_TARGET_PLATFORMS):
        constraint = PLATFORM_CONSTRAINTS.get(name, {})
        platforms.append(PlatformInfo(
            platform=name,
            content_type=constraint.get("content_type", name),
            char_limit=constraint.get("char_limit"),
            description=constraint.get("rules", f"Repurpose content for {name}"),
        ))
    return platforms
