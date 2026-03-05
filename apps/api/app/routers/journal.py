"""Experience Journal Router — Slice 90 + 039 (journal usage tracking).

Captures user's real experiences: call recordings, transcripts, notes, case studies.
Agents query this before writing to ground content in real experience.

Endpoints (all JWT-protected):
  GET    /journal                 — list journal entries for a brand (with usage stats)
  POST   /journal                 — create an entry (text-based; audio handled by voice_notes.py)
  DELETE /journal/{id}            — delete an entry
  PATCH  /journal/{id}/pin        — toggle pin (pinned entries always included in pipeline)
  GET    /journal/suggest         — AI-suggest best entries for a given topic
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
    times_used: int = 0
    last_used_at: Optional[str] = None
    pinned: bool = False


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
        times_used=row.get("times_used") or 0,
        last_used_at=str(row["last_used_at"]) if row.get("last_used_at") else None,
        pinned=bool(row.get("pinned", False)),
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


@router.patch("/journal/{entry_id}/pin", response_model=JournalEntryResponse)
async def toggle_pin_journal_entry(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Toggle the pinned flag on a journal entry.

    Pinned entries are always included when the pipeline runs Phase 2 (Write),
    regardless of how many times they've been used. Use this to force the agent
    to draw from a specific story or client win every time.
    """
    if not _UUID_RE.match(entry_id):
        raise HTTPException(400, "Invalid entry_id")

    sb = get_admin_client()

    # Fetch current state (IDOR: enforce user_id)
    existing = (
        sb.table("experience_journal")
        .select("id, pinned, user_id")
        .eq("id", entry_id)
        .eq("user_id", user.id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Entry not found or not yours")

    new_pinned = not existing.data.get("pinned", False)
    result = (
        sb.table("experience_journal")
        .update({"pinned": new_pinned})
        .eq("id", entry_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(500, "Failed to update pin status")

    logger.info(
        "Journal entry %s pinned=%s user=%s", entry_id, new_pinned, user.id
    )
    return _row_to_response(result.data[0])


class SuggestResponse(BaseModel):
    suggested_ids: List[str]
    entries: List[JournalEntryResponse]
    reasoning: str


@router.get("/journal/suggest", response_model=SuggestResponse)
async def suggest_journal_entries(
    brand_id: str,
    topic: str = "",
    limit: int = 5,
    user: CurrentUser = Depends(get_current_user),
):
    """AI-suggest the best journal entries for a given topic.

    Returns a ranked list of entries the agent would use if the pipeline
    ran right now, along with reasoning. Use this before a pipeline run
    to preview what stories will be used, then pin/unpin as needed.
    """
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    limit = min(max(limit, 1), 10)

    from app.services.jumbo_pipeline import get_relevant_experiences

    context, selected_ids = get_relevant_experiences(
        user_id=user.id,
        brand_id=brand_id,
        topic=topic,
        max_entries=limit,
    )

    if not selected_ids:
        return SuggestResponse(suggested_ids=[], entries=[], reasoning="No journal entries found for this brand.")

    # Fetch full entry details for the selected IDs
    sb = get_admin_client()
    rows_result = (
        sb.table("experience_journal")
        .select("*")
        .in_("id", selected_ids)
        .eq("user_id", user.id)
        .execute()
    )

    # Preserve the order returned by the AI ranker
    id_order = {eid: i for i, eid in enumerate(selected_ids)}
    rows = sorted(rows_result.data or [], key=lambda r: id_order.get(r["id"], 999))

    pinned_count = sum(1 for r in rows if r.get("pinned"))
    never_used = sum(1 for r in rows if (r.get("times_used") or 0) == 0)

    if topic.strip():
        reasoning = (
            f"AI selected {len(rows)} entries most relevant to your topic. "
            f"{pinned_count} pinned (always included). "
            f"{never_used} never used before (fresh material)."
        )
    else:
        reasoning = (
            f"Selected {len(rows)} entries: {pinned_count} pinned + "
            f"{never_used} never-used + least-recently-used. "
            "Provide a topic for AI relevance ranking."
        )

    return SuggestResponse(
        suggested_ids=selected_ids,
        entries=[_row_to_response(r) for r in rows],
        reasoning=reasoning,
    )
