"""Account Manager Router — Slice 98.

Endpoints:
  POST /account-manager/analyze          — analyze transcript → action plan
  GET  /account-manager/sessions         — list sessions for a brand
  GET  /account-manager/sessions/{id}    — get single session
  PATCH /account-manager/sessions/{id}   — update action plan (approve/deny items)
  POST /account-manager/sessions/{id}/execute — execute approved actions

Security: A01 IDOR, A03 UUID, A07 JWT.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.account_manager")

router = APIRouter(prefix="/account-manager", tags=["account-manager"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class AnalyzeBody(BaseModel):
    brand_id: str
    transcript: str = Field(..., min_length=10)
    call_date: Optional[str] = None
    intake_form_id: Optional[str] = None


class UpdateSessionBody(BaseModel):
    actions: List[Dict[str, Any]]
    status: Optional[str] = None


# ── POST /account-manager/analyze ────────────────────────────────────────


@router.post("/analyze")
async def analyze_transcript(
    body: AnalyzeBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Analyze a client call transcript and create an action plan session."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    if body.intake_form_id and not _UUID_RE.match(body.intake_form_id):
        raise HTTPException(400, "Invalid intake_form_id — must be UUID")

    from app.services.account_manager import analyze_transcript as _analyze
    try:
        session = await _analyze(
            brand_id=body.brand_id,
            user_id=user.id,
            transcript=body.transcript,
            call_date=body.call_date,
            intake_form_id=body.intake_form_id,
        )
        return session
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


# ── GET /account-manager/sessions ────────────────────────────────────────


@router.get("/sessions")
async def list_sessions(
    brand_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
):
    """List all account manager sessions for a brand."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    from app.services.account_manager import list_sessions as _list
    return _list(user_id=user.id, brand_id=brand_id)


# ── GET /account-manager/sessions/{session_id} ───────────────────────────


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single account manager session."""
    if not _UUID_RE.match(session_id):
        raise HTTPException(400, "Invalid session_id — must be UUID")
    from app.services.account_manager import get_session as _get
    try:
        return _get(session_id=session_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


# ── PATCH /account-manager/sessions/{session_id} ─────────────────────────


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: UpdateSessionBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Update action items (approve/deny) and optionally session status."""
    if not _UUID_RE.match(session_id):
        raise HTTPException(400, "Invalid session_id — must be UUID")
    from app.services.account_manager import update_action_plan
    return update_action_plan(
        session_id=session_id,
        user_id=user.id,
        actions=body.actions,
        status=body.status,
    )
