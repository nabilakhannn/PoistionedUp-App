"""Client Deliverables Router — Slice 98.

Endpoints:
  POST /deliverables/proposal             — generate HTML proposal
  POST /deliverables/landing-page         — generate HTML landing page
  POST /deliverables/nurture-sequence     — generate 5-email nurture
  GET  /deliverables                      — list deliverables for a brand
  GET  /deliverables/{id}                 — get single deliverable
  GET  /share/{share_token}               — PUBLIC: preview deliverable by token

Security: A01 IDOR, A03 UUID, A07 JWT on private routes.
          Share token is 64-char random hex — public route is intentional.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.client_deliverables")

router = APIRouter(tags=["client-deliverables"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


class ProposalBody(BaseModel):
    session_id: str
    brand_id: str


class LandingPageBody(BaseModel):
    brand_id: str


class NurtureBody(BaseModel):
    brand_id: str
    lead_context: str


# ── POST /deliverables/proposal ───────────────────────────────────────────


@router.post("/deliverables/proposal")
async def generate_proposal(
    body: ProposalBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a full HTML client proposal from an account manager session."""
    if not _UUID_RE.match(body.session_id):
        raise HTTPException(400, "Invalid session_id — must be UUID")
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_deliverables import generate_proposal as _gen
    try:
        return await _gen(session_id=body.session_id, brand_id=body.brand_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── POST /deliverables/landing-page ──────────────────────────────────────


@router.post("/deliverables/landing-page")
async def generate_landing_page(
    body: LandingPageBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a responsive HTML landing page from the brand dossier."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_deliverables import generate_landing_page as _gen
    try:
        return await _gen(brand_id=body.brand_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── POST /deliverables/nurture-sequence ──────────────────────────────────


@router.post("/deliverables/nurture-sequence")
async def generate_nurture(
    body: NurtureBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a 5-email nurture sequence using emotional journals."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_deliverables import generate_nurture_sequence as _gen
    try:
        return await _gen(brand_id=body.brand_id, user_id=user.id, lead_context=body.lead_context)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── GET /deliverables ────────────────────────────────────────────────────


@router.get("/deliverables")
async def list_deliverables(
    brand_id: str = Query(...),
    deliverable_type: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
):
    """List all client deliverables for a brand."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.client_deliverables import list_deliverables as _list
    return _list(user_id=user.id, brand_id=brand_id, deliverable_type=deliverable_type)


# ── GET /deliverables/{id} ───────────────────────────────────────────────


@router.get("/deliverables/{deliverable_id}")
async def get_deliverable(
    deliverable_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single deliverable (authenticated)."""
    if not _UUID_RE.match(deliverable_id):
        raise HTTPException(400, "Invalid deliverable_id — must be UUID")
    from app.services.client_deliverables import get_deliverable as _get
    try:
        return _get(deliverable_id=deliverable_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── GET /share/{share_token} — PUBLIC ────────────────────────────────────


@router.get("/share/{share_token}")
async def public_share(share_token: str):
    """PUBLIC: preview a deliverable by share token. No auth required."""
    if not _TOKEN_RE.match(share_token):
        raise HTTPException(400, "Invalid share token")
    from app.services.client_deliverables import get_deliverable_by_token
    try:
        d = get_deliverable_by_token(share_token)
    except ValueError:
        raise HTTPException(404, "Deliverable not found")

    content = d.get("content", "")
    dtype = d.get("deliverable_type", "")

    # HTML deliverables (proposals, landing pages) — serve as HTML response
    if dtype in ("proposal", "landing_page") and content.strip().startswith("<!DOCTYPE"):
        return HTMLResponse(content=content)

    # JSON deliverables (nurture sequences) — wrap in a simple viewer
    if dtype == "nurture_sequence":
        import json
        try:
            seq = json.loads(content)
        except Exception:
            seq = []
        emails_html = "".join(
            f"<div style='margin-bottom:2rem;padding:1.5rem;background:#1a1a2e;border-radius:12px;'>"
            f"<div style='color:#818cf8;font-size:0.8rem;margin-bottom:0.5rem'>Email {e.get('email_number',i+1)} — Day {e.get('day','')}</div>"
            f"<div style='font-size:1.1rem;font-weight:600;margin-bottom:1rem'>{e.get('subject','')}</div>"
            f"<div style='color:#94a3b8;white-space:pre-line'>{e.get('body','')}</div>"
            f"<div style='margin-top:1rem;padding:0.75rem;background:#0f0f1a;border-radius:8px;color:#818cf8'><strong>CTA:</strong> {e.get('cta','')}</div>"
            f"</div>"
            for i, e in enumerate(seq)
        )
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nurture Sequence</title>
<style>body{{font-family:system-ui,sans-serif;background:#0a0a0a;color:#e2e8f0;padding:2rem;max-width:700px;margin:0 auto}}</style>
</head><body><h1 style="color:#818cf8">Email Nurture Sequence</h1>{emails_html}</body></html>"""
        return HTMLResponse(content=html)

    # Fallback — JSON response
    return d


# ── PATCH /deliverables/{id}/status — lifecycle tracking ─────────────────

_VALID_PROPOSAL_STATUSES = {"draft", "sent", "accepted", "rejected", "closed_won", "closed_lost"}


class DeliverableStatusBody(BaseModel):
    proposal_status: str
    deal_value: Optional[float] = None


@router.patch("/deliverables/{deliverable_id}/status")
async def update_deliverable_status(
    deliverable_id: str,
    body: DeliverableStatusBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Update proposal lifecycle status (draft -> sent -> accepted/rejected -> closed)."""
    if not _UUID_RE.match(deliverable_id):
        raise HTTPException(400, "Invalid deliverable_id — must be UUID")
    if body.proposal_status not in _VALID_PROPOSAL_STATUSES:
        raise HTTPException(
            400,
            f"Invalid status. Must be one of: {sorted(_VALID_PROPOSAL_STATUSES)}",
        )

    from app.deps import get_admin_client
    sb = get_admin_client()

    update_data = {"proposal_status": body.proposal_status}
    if body.deal_value is not None:
        update_data["deal_value"] = body.deal_value

    result = (
        sb.table("agent_deliverables")
        .update(update_data)
        .eq("id", deliverable_id)
        .eq("user_id", user.id)  # IDOR guard
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Deliverable not found")

    return {"ok": True, "proposal_status": body.proposal_status, "deal_value": body.deal_value}


# ── POST /deliverables/{id}/regenerate — create new version ──────────────


@router.post("/deliverables/{deliverable_id}/regenerate")
async def regenerate_deliverable(
    deliverable_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Regenerate a deliverable (creates a new version with incremented version number)."""
    if not _UUID_RE.match(deliverable_id):
        raise HTTPException(400, "Invalid deliverable_id — must be UUID")

    from app.deps import get_admin_client
    sb = get_admin_client()

    # Fetch original deliverable
    original = (
        sb.table("agent_deliverables")
        .select("deliverable_type, brand_id, metadata")
        .eq("id", deliverable_id)
        .eq("user_id", user.id)  # IDOR guard
        .limit(1)
        .execute()
    )
    if not original.data:
        raise HTTPException(404, "Deliverable not found")

    row = original.data[0]
    dtype = row.get("deliverable_type", "")
    brand_id = row.get("brand_id", "")
    metadata = row.get("metadata") or {}

    if dtype == "proposal":
        session_id = metadata.get("session_id")
        if not session_id:
            raise HTTPException(400, "Cannot regenerate: original has no session_id in metadata")
        from app.services.client_deliverables import generate_proposal as _gen
        return await _gen(session_id=session_id, brand_id=brand_id, user_id=user.id)
    elif dtype == "landing_page":
        from app.services.client_deliverables import generate_landing_page as _gen_lp
        return await _gen_lp(brand_id=brand_id, user_id=user.id)
    elif dtype == "nurture_sequence":
        lead_context = metadata.get("lead_context", "")
        from app.services.client_deliverables import generate_nurture_sequence as _gen_ns
        return await _gen_ns(brand_id=brand_id, user_id=user.id, lead_context=lead_context)
    else:
        raise HTTPException(400, f"Regeneration not supported for type: {dtype}")
