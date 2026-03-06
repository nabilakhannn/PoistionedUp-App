"""Video Content Router — Slice 108.

Endpoints for video script generation, HeyGen avatars, and Veo3.1 AI video.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.video_content")

router = APIRouter(prefix="/video", tags=["video"])


# ── Schemas ──────────────────────────────────────────────────────────


class ScriptRequest(BaseModel):
    brand_id: str
    topic: str
    video_type: str = "talking_head"
    duration_seconds: int = 60
    platform: str = "linkedin"


class HeyGenRequest(BaseModel):
    script: str
    avatar_id: str = "default"
    voice_id: str = "default"
    emotion: str = "friendly"
    speed: float = 1.0
    dimensions: str = "1080x1920"


class VeoRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "9:16"
    reference_image_url: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/capabilities")
async def get_capabilities():
    """Check which video services are available."""
    from app.services.video_content import get_video_capabilities
    return get_video_capabilities()


@router.post("/script")
async def create_script(
    body: ScriptRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a video script using brand context."""
    from app.services.video_content import generate_video_script
    try:
        return generate_video_script(
            brand_id=body.brand_id,
            user_id=user.id,
            topic=body.topic,
            video_type=body.video_type,
            duration_seconds=body.duration_seconds,
            platform=body.platform,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/heygen/generate")
async def generate_heygen(
    body: HeyGenRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit a HeyGen avatar video generation."""
    from app.services.video_content import generate_heygen_video
    result = generate_heygen_video(
        script=body.script,
        avatar_id=body.avatar_id,
        voice_id=body.voice_id,
        emotion=body.emotion,
        speed=body.speed,
        dimensions=body.dimensions,
    )
    if result.get("error") and not result.get("available", True):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/heygen/status/{task_id}")
async def poll_heygen(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Poll HeyGen video generation status."""
    from app.services.video_content import poll_heygen_status
    return poll_heygen_status(task_id)


@router.post("/veo/generate")
async def generate_veo(
    body: VeoRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit a Veo3.1 AI video generation."""
    from app.services.video_content import generate_veo_video
    result = generate_veo_video(
        prompt=body.prompt,
        aspect_ratio=body.aspect_ratio,
        reference_image_url=body.reference_image_url,
    )
    if result.get("error") and not result.get("available", True):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/veo/status/{task_id}")
async def poll_veo(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Poll Veo3.1 video generation status."""
    from app.services.video_content import poll_veo_status
    return poll_veo_status(task_id)
