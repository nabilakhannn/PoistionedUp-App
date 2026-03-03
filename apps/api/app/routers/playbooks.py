"""Playbooks router — Slice 85.

Endpoints:
  GET    /playbooks/                     list all playbooks for user
  GET    /playbooks/{agent_id}           get a single playbook
  POST   /playbooks/seed                 seed default playbooks for this user
  PATCH  /playbooks/{agent_id}/propose   write a pending edit
  POST   /playbooks/{agent_id}/apply     promote pending edit → active
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/playbooks", tags=["playbooks"])


class ProposeEditBody(BaseModel):
    new_md: str


# ── GET /playbooks/ ───────────────────────────────────────────────

@router.get("/")
async def list_playbooks(user: CurrentUser = Depends(get_current_user)):
    """List all playbooks for the authenticated user."""
    from app.services.playbooks import list_playbooks as _list
    return _list(user.id)


# ── GET /playbooks/{agent_id} ─────────────────────────────────────

@router.get("/{agent_id}")
async def get_playbook(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single playbook by agent ID."""
    from app.services.playbooks import get_playbook as _get
    playbook = _get(agent_id, user.id)
    if not playbook:
        raise HTTPException(status_code=404, detail=f"Playbook not found for agent {agent_id!r}")
    return playbook


# ── POST /playbooks/seed ──────────────────────────────────────────

@router.post("/seed")
async def seed_playbooks(user: CurrentUser = Depends(get_current_user)):
    """Seed default playbooks for all 8 agents. Safe to call multiple times."""
    from app.services.playbooks import seed_default_playbooks
    count = seed_default_playbooks(user.id)
    return {"seeded": count, "message": f"Seeded {count} default playbooks"}


# ── PATCH /playbooks/{agent_id}/propose ──────────────────────────

@router.patch("/{agent_id}/propose")
async def propose_edit(
    agent_id: str,
    body: ProposeEditBody,
    user: CurrentUser = Depends(get_current_user),
):
    """Propose a playbook edit. Does not activate until /apply is called."""
    from app.services.playbooks import propose_edit as _propose
    try:
        playbook = _propose(agent_id, user.id, body.new_md)
        return {"status": "pending", "agent_id": agent_id, "playbook": playbook}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── POST /playbooks/{agent_id}/apply ─────────────────────────────

@router.post("/{agent_id}/apply")
async def apply_edit(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Promote the pending playbook edit to active. Increments version."""
    from app.services.playbooks import apply_edit as _apply
    try:
        playbook = _apply(agent_id, user.id)
        return {"status": "applied", "agent_id": agent_id, "version": playbook.get("version"), "playbook": playbook}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
