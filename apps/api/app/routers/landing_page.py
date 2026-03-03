"""Landing Page Generator Router — Slice 93.

Endpoints (all JWT-protected):
  POST /landing-page/tools      — Research best free landing page builders (Perplexity)
  POST /landing-page/structure  — Phase 1: page blueprint from Haiku (near-free)
  POST /landing-page/generate   — Phase 2: full HTML from Sonnet 4.6
  GET  /landing-page/history    — Recent pages for a brand
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.landing_page")

router = APIRouter(tags=["landing-page"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_PAGE_GOALS = {"capture_email", "book_call", "sell_product", "build_awareness", "other"}


# ── Schemas ────────────────────────────────────────────────────────────────


class StructureRequest(BaseModel):
    brand_id: str
    description: str = Field(..., min_length=5, max_length=1000)
    page_goal: str = Field(default="other")
    target_audience: str = Field(default="", max_length=500)
    inspiration_url: Optional[str] = Field(default=None, max_length=2000)


class GenerateRequest(BaseModel):
    brand_id: str
    description: str = Field(..., min_length=5, max_length=1000)
    structure: Dict[str, Any]  # Phase 1 output passed from frontend


class GenerateResponse(BaseModel):
    id: Optional[str] = None
    html: str
    title: str
    model_used: Optional[str] = None
    error: Optional[str] = None


class LandingPageRecord(BaseModel):
    id: str
    brand_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    page_goal: Optional[str] = None
    model_used: Optional[str] = None
    created_at: str


def _row_to_record(row: dict) -> LandingPageRecord:
    return LandingPageRecord(
        id=row["id"],
        brand_id=row.get("brand_id"),
        title=row.get("title", "Untitled"),
        description=row.get("description"),
        page_goal=row.get("page_goal"),
        model_used=row.get("model_used"),
        created_at=str(row.get("created_at", "")),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/landing-page/tools")
async def research_tools(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Research best free landing page builders via Perplexity.

    Returns a comparison table (name, free tier, drag & drop, custom domain,
    template count, score 1-10). Falls back to curated list if no API key.
    """
    from app.services.landing_page import research_tools as _research
    result = _research()
    logger.info("Tool research completed for user=%s source=%s", user.id, result.get("source"))
    return result


@router.post("/landing-page/structure")
async def structure_page(
    body: StructureRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Phase 1: generate a locked page blueprint using Claude Haiku.

    Near-free — no HTML generation. Returns a section-by-section blueprint
    with headline directions, CTAs, tone, and color hint.

    Optionally analyzes an inspiration_url via Perplexity (SSRF-validated).
    """
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    safe_goal = body.page_goal if body.page_goal in VALID_PAGE_GOALS else "other"

    from app.services.landing_page import structure_page as _structure
    result = _structure(
        description=body.description,
        page_goal=safe_goal,
        target_audience=body.target_audience,
        brand_id=body.brand_id,
        inspiration_url=body.inspiration_url,
        user_id=user.id,
    )

    logger.info(
        "Page structured user=%s brand=%s sections=%d error=%s",
        user.id, body.brand_id, len(result.get("sections", [])), result.get("error"),
    )
    return result


@router.post("/landing-page/generate", response_model=GenerateResponse)
async def generate_page(
    body: GenerateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> GenerateResponse:
    """Phase 2: generate full self-contained HTML from the page blueprint.

    Fetches brand profile for voice/ICP grounding.
    Returns {id, html, title, model_used, error}.
    """
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    if not body.structure:
        raise HTTPException(400, "structure is required — call /landing-page/structure first")

    from app.services.landing_page import generate_page as _generate
    result = _generate(
        structure=body.structure,
        description=body.description,
        brand_id=body.brand_id,
        user_id=user.id,
    )

    logger.info(
        "Page generated user=%s brand=%s model=%s error=%s",
        user.id, body.brand_id, result.get("model_used"), result.get("error"),
    )

    return GenerateResponse(
        id=result.get("id"),
        html=result.get("html", ""),
        title=result.get("title", "Landing Page"),
        model_used=result.get("model_used"),
        error=result.get("error"),
    )


@router.get("/landing-page/history", response_model=List[LandingPageRecord])
async def list_pages(
    brand_id: str,
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
) -> List[LandingPageRecord]:
    """List recent generated landing pages for a brand, newest first."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    limit = min(limit, 50)
    sb = get_admin_client()
    result = (
        sb.table("generated_landing_pages")
        .select("id,brand_id,title,description,page_goal,model_used,created_at")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_record(row) for row in (result.data or [])]
