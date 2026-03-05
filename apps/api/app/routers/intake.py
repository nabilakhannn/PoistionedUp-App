"""Intake Router — Slice 97.

Manages client intake forms — public shareable forms clients fill in before calls.

Public endpoints (no auth):
  GET  /intake/{share_token}     — fetch form schema + current values
  POST /intake/{share_token}     — client submits form

Authenticated endpoints (JWT required):
  POST /intake/create            — SB creates a new form + gets share link
  GET  /intake/my                — SB views submitted form for a brand

Security: A01 IDOR (.eq user_id on auth routes), A07 JWT on private routes,
          share_token is 64-char random hex (not guessable).
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.intake")

router = APIRouter(prefix="/intake", tags=["intake"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


# ── Schemas ────────────────────────────────────────────────────────────────


class IntakeSubmit(BaseModel):
    client_name: Optional[str] = None
    business_name: Optional[str] = None
    industry: Optional[str] = None
    current_revenue: Optional[str] = None
    primary_offer: Optional[str] = None
    offer_price: Optional[str] = None
    secondary_offers: Optional[str] = None
    target_audience: Optional[str] = None
    best_3_clients: Optional[str] = None
    traffic_sources: Optional[str] = None
    funnel_status: Optional[str] = None
    biggest_frustration: Optional[str] = None
    goals: Optional[str] = None
    tech_stack: Optional[str] = None
    timeline: Optional[str] = None
    additional_notes: Optional[str] = None


class IntakeCreate(BaseModel):
    brand_id: str
    client_name: Optional[str] = None


# ── Public endpoints ───────────────────────────────────────────────────────


@router.get("/{share_token}")
async def get_public_form(share_token: str):
    """Return form schema + existing values for a share token. No auth required."""
    if not _TOKEN_RE.match(share_token):
        raise HTTPException(400, "Invalid share token")
    sb = get_admin_client()
    row = (
        sb.table("client_intake_forms")
        .select(
            "id, client_name, business_name, industry, current_revenue, "
            "primary_offer, offer_price, secondary_offers, target_audience, "
            "best_3_clients, traffic_sources, funnel_status, biggest_frustration, "
            "goals, tech_stack, timeline, additional_notes, submitted_at, created_at"
        )
        .eq("share_token", share_token)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise HTTPException(404, "Form not found")
    return row.data[0]


@router.post("/{share_token}")
async def submit_public_form(share_token: str, body: IntakeSubmit):
    """Client submits the intake form. No auth required."""
    if not _TOKEN_RE.match(share_token):
        raise HTTPException(400, "Invalid share token")
    sb = get_admin_client()

    # Verify form exists
    existing = (
        sb.table("client_intake_forms")
        .select("id, submitted_at")
        .eq("share_token", share_token)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Form not found")

    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    patch["submitted_at"] = "now()"

    sb.table("client_intake_forms").update(patch).eq("share_token", share_token).execute()
    return {"status": "submitted", "message": "Thanks! Your coach will review this before your call."}


# ── Authenticated endpoints ────────────────────────────────────────────────


@router.post("/create")
async def create_intake_form(
    body: IntakeCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new intake form for a brand and return the share link."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")

    sb = get_admin_client()
    row = (
        sb.table("client_intake_forms")
        .insert({
            "user_id": user.id,
            "brand_id": body.brand_id,
            "client_name": body.client_name,
        })
        .execute()
    )
    if not row.data:
        raise HTTPException(500, "Failed to create intake form")

    form = row.data[0]
    return {
        "id": form["id"],
        "share_token": form["share_token"],
        "share_url": f"/intake/{form['share_token']}",
    }


@router.get("/my")
async def get_my_form(
    brand_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Return the latest intake form for a brand (SB viewing client submission)."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")

    sb = get_admin_client()
    row = (
        sb.table("client_intake_forms")
        .select("*")
        .eq("user_id", user.id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]
