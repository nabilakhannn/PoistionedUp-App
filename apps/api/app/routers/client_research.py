"""Client Research Router — Slice 97.

Endpoints:
  POST /client-research/run              — run full 5-layer research
  GET  /client-research/report/{brand_id} — get current dossier
  POST /client-research/refresh/{brand_id} — regenerate one section

Security: A01 IDOR, A03 UUID validation, A07 JWT, A10 SSRF (in service layer).
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.client_research")

router = APIRouter(prefix="/client-research", tags=["client-research"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ResearchRunBody(BaseModel):
    brand_id: str
    linkedin_url: str
    website_url: Optional[str] = None
    offer_description: Optional[str] = None
    best_clients: Optional[str] = None
    content_goal: Optional[str] = None


class RefreshBody(BaseModel):
    section: str
    # hormozi | competitors | anxiety_list | benefit_list
    # first_week_angles | emotional_pain_journal | emotional_win_journal


# ── POST /client-research/run ─────────────────────────────────────────────


@router.post("/run")
async def run_research(
    body: ResearchRunBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Run deep 5-layer client research. Takes ~60-90 seconds."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    if not body.linkedin_url.startswith("https://"):
        raise HTTPException(400, "linkedin_url must start with https://")

    from app.services.client_researcher import research_client
    try:
        dossier = await research_client(
            brand_id=body.brand_id,
            user_id=user.id,
            linkedin_url=body.linkedin_url,
            website_url=body.website_url,
            offer_description=body.offer_description,
            best_clients=body.best_clients,
            content_goal=body.content_goal,
        )
        return {"status": "ok", "brand_id": body.brand_id, "dossier": dossier}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


# ── GET /client-research/report/{brand_id} ────────────────────────────────


@router.get("/report/{brand_id}")
async def get_report(
    brand_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return the current client intelligence dossier for a brand."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_researcher import get_report as _get
    try:
        return _get(brand_id=brand_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── POST /client-research/refresh/{brand_id} ─────────────────────────────


@router.post("/refresh/{brand_id}")
async def refresh_section(
    brand_id: str,
    body: RefreshBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Regenerate a single section of the client dossier."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_researcher import refresh_section as _refresh
    try:
        result = await _refresh(brand_id=brand_id, user_id=user.id, section=body.section)
        return {"status": "ok", "brand_id": brand_id, **result}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))
