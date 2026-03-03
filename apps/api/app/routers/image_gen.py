"""Image Generation Router — Slice 91a.

Endpoints (all JWT-protected):
  POST /image-gen/generate    — Full pipeline: engineer prompt → call API → save
  POST /image-gen/structure   — Preview prompt engineering only (zero image cost)
  GET  /image-gen/history     — Last 20 generated images for a brand
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.image_gen")

router = APIRouter(tags=["image-gen"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_STYLES = {"photorealistic", "cinematic", "branded", "editorial", "lifestyle"}
VALID_FORMATS = {"square", "landscape", "portrait", "story"}


# ── Schemas ────────────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    brand_id: str
    description: str = Field(..., min_length=5, max_length=1000)
    style: str = Field(default="photorealistic")
    img_format: str = Field(default="square", alias="format")

    model_config = {"populate_by_name": True}


class StructureRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=1000)
    style: str = Field(default="photorealistic")
    brand_id: str = ""


class GenerateResponse(BaseModel):
    url: Optional[str] = None
    structured_prompt: str
    model_used: Optional[str] = None
    error: Optional[str] = None


class GeneratedImageRecord(BaseModel):
    id: str
    brand_id: Optional[str] = None
    description: str
    structured_prompt: str
    image_url: Optional[str] = None
    style: str
    img_format: str = Field(alias="format")
    model_used: Optional[str] = None
    created_at: str

    model_config = {"populate_by_name": True}


def _row_to_record(row: dict) -> GeneratedImageRecord:
    return GeneratedImageRecord(
        id=row["id"],
        brand_id=row.get("brand_id"),
        description=row.get("description", ""),
        structured_prompt=row.get("structured_prompt", "{}"),
        image_url=row.get("image_url"),
        style=row.get("style", "photorealistic"),
        format=row.get("format", "square"),
        model_used=row.get("model_used"),
        created_at=str(row.get("created_at", "")),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/image-gen/structure")
async def structure_prompt(
    body: StructureRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Preview Claude's structured prompt without calling the image API.

    Returns the 9-variable JSON breakdown (subject, camera, lighting, etc.)
    so users can see and understand what will be sent before committing.
    Zero image generation cost.
    """
    safe_style = body.style if body.style in VALID_STYLES else "photorealistic"

    from app.services.image_gen import structure_prompt_only
    result = structure_prompt_only(
        description=body.description,
        style=safe_style,
        brand_context="",
    )
    return result


@router.post("/image-gen/generate", response_model=GenerateResponse)
async def generate_image(
    body: GenerateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> GenerateResponse:
    """Full pipeline: engineer prompt → call Higgsfield/Gemini → save to DB.

    Returns {url, structured_prompt, model_used, error}.
    """
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    safe_style = body.style if body.style in VALID_STYLES else "photorealistic"
    safe_format = body.img_format if body.img_format in VALID_FORMATS else "square"

    from app.services.image_gen import generate_image as _gen
    result = _gen(
        description=body.description,
        style=safe_style,
        img_format=safe_format,
        brand_context="",
        user_id=user.id,
        brand_id=body.brand_id,
    )

    logger.info(
        "Image generated user=%s brand=%s model=%s error=%s",
        user.id, body.brand_id, result.get("model_used"), result.get("error"),
    )

    return GenerateResponse(
        url=result.get("url"),
        structured_prompt=result.get("structured_prompt", "{}"),
        model_used=result.get("model_used"),
        error=result.get("error"),
    )


@router.get("/image-gen/history", response_model=List[GeneratedImageRecord])
async def list_generated_images(
    brand_id: str,
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
) -> List[GeneratedImageRecord]:
    """List recent generated images for a brand, newest first."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    limit = min(limit, 50)

    sb = get_admin_client()
    result = (
        sb.table("generated_images")
        .select("*")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_record(row) for row in (result.data or [])]
