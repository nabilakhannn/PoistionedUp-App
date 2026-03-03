"""Experience Journal Router — Slice 90.

Captures user's real experiences: call recordings, transcripts, notes, case studies.
Agents query this before writing to ground content in real experience.

Endpoints (all JWT-protected):
  GET    /journal          — list journal entries for a brand
  POST   /journal          — create an entry (text-based; audio handled by voice_notes.py)
  DELETE /journal/{id}     — delete an entry
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.journal")

router = APIRouter(tags=["journal"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_SOURCE_TYPES = {"call_recording", "transcript", "note", "case_study"}


# ── Schemas ────────────────────────────────────────────────────────────────


class JournalEntryResponse(BaseModel):
    id: str
    brand_id: str
    title: Optional[str] = None
    source_type: str
    raw_content: str
    insights: list
    tags: List[str]
    created_at: str


class CreateJournalRequest(BaseModel):
    brand_id: str
    title: Optional[str] = Field(default=None, max_length=255)
    source_type: str = Field(default="note")
    raw_content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


def _row_to_response(row: dict) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=row["id"],
        brand_id=row["brand_id"],
        title=row.get("title"),
        source_type=row.get("source_type", "note"),
        raw_content=row.get("raw_content", ""),
        insights=row.get("insights") or [],
        tags=row.get("tags") or [],
        created_at=str(row.get("created_at", "")),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/journal", response_model=List[JournalEntryResponse])
async def list_journal(
    brand_id: str,
    source_type: Optional[str] = None,
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """List journal entries for a brand, newest first."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    limit = min(limit, 100)

    sb = get_admin_client()
    q = (
        sb.table("experience_journal")
        .select("*")
        .eq("brand_id", brand_id)
        .eq("user_id", user.id)
    )
    if source_type and source_type in VALID_SOURCE_TYPES:
        q = q.eq("source_type", source_type)

    result = q.order("created_at", desc=True).limit(limit).execute()
    return [_row_to_response(row) for row in (result.data or [])]


@router.post("/journal", response_model=JournalEntryResponse, status_code=201)
async def create_journal_entry(
    body: CreateJournalRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a journal entry (note, transcript, or case study)."""
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    source_type = body.source_type if body.source_type in VALID_SOURCE_TYPES else "note"

    sb = get_admin_client()
    row = {
        "user_id": user.id,
        "brand_id": body.brand_id,
        "title": body.title[:255] if body.title else None,
        "source_type": source_type,
        "raw_content": body.raw_content,
        "tags": body.tags,
        "insights": [],
    }

    result = sb.table("experience_journal").insert(row).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create journal entry")

    logger.info(
        "Journal entry created user=%s brand=%s type=%s",
        user.id, body.brand_id, source_type,
    )
    return _row_to_response(result.data[0])


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal_entry(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a journal entry."""
    if not _UUID_RE.match(entry_id):
        raise HTTPException(400, "Invalid entry_id")

    sb = get_admin_client()
    result = (
        sb.table("experience_journal")
        .delete()
        .eq("id", entry_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Entry not found or not yours")

    return None
