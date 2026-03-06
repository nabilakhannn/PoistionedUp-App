"""Story Bank Router — Slice 109.

Extends the journal system with AI-powered story extraction.
Stories are extracted from experience_journal entries and stored in
the extracted_stories JSONB column for prompt injection.

Endpoints (all JWT-protected):
  POST   /stories/ingest         — Create a new entry + auto-extract stories
  GET    /stories                — List all entries with extracted stories
  GET    /stories/search         — Search extracted stories by topic/theme
  POST   /stories/{id}/extract   — Re-extract stories from an existing entry
  DELETE /stories/{id}           — Delete an entry
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.stories")

router = APIRouter(tags=["stories"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_SOURCE_TYPES = {
    "call_recording", "transcript", "note", "case_study",
    "idea", "opinion", "quote", "take", "framework",
}


# ── Schemas ────────────────────────────────────────────────────────────────


class StoryEntryResponse(BaseModel):
    id: str
    brand_id: str
    title: Optional[str] = None
    source_type: str
    raw_content: str
    extracted_stories: list
    tags: List[str]
    story_tags: List[str]
    pinned: bool = False
    created_at: str


class IngestRequest(BaseModel):
    brand_id: str
    title: Optional[str] = Field(default=None, max_length=255)
    source_type: str = Field(default="note")
    raw_content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class ExtractedStory(BaseModel):
    summary: str
    theme: str
    emotion: str
    key_quote: str
    usable_hook: str


class SearchResponse(BaseModel):
    stories: list
    total: int


def _row_to_response(row: dict) -> StoryEntryResponse:
    return StoryEntryResponse(
        id=row["id"],
        brand_id=row["brand_id"],
        title=row.get("title"),
        source_type=row.get("source_type", "note"),
        raw_content=row.get("raw_content", ""),
        extracted_stories=row.get("extracted_stories") or [],
        tags=row.get("tags") or [],
        story_tags=row.get("story_tags") or [],
        pinned=bool(row.get("pinned", False)),
        created_at=str(row.get("created_at", "")),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/stories/ingest", response_model=StoryEntryResponse, status_code=201)
async def ingest_story(
    body: IngestRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new Story Bank entry and auto-extract stories via AI."""
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
        "extracted_stories": [],
        "story_tags": [],
    }

    result = sb.table("experience_journal").insert(row).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create story entry")

    entry_id = result.data[0]["id"]

    # Auto-extract stories in background (don't block response)
    try:
        from app.services.story_extractor import extract_and_save
        stories = await extract_and_save(entry_id, user.id)
        # Re-fetch to get updated row
        updated = (
            sb.table("experience_journal")
            .select("*")
            .eq("id", entry_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if updated.data:
            return _row_to_response(updated.data[0])
    except Exception as exc:
        logger.warning("Auto-extract failed for entry=%s: %s", entry_id, str(exc)[:200])

    logger.info("Story ingested user=%s brand=%s type=%s", user.id, body.brand_id, source_type)
    return _row_to_response(result.data[0])


@router.get("/stories", response_model=List[StoryEntryResponse])
async def list_stories(
    brand_id: str,
    source_type: Optional[str] = None,
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
):
    """List all Story Bank entries for a brand, newest first."""
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


@router.get("/stories/search", response_model=SearchResponse)
async def search_stories(
    brand_id: str,
    topic: str = "",
    limit: int = 5,
    user: CurrentUser = Depends(get_current_user),
):
    """Search extracted stories by topic/theme relevance."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    from app.services.story_extractor import search_stories_by_theme

    stories = search_stories_by_theme(
        user_id=user.id,
        brand_id=brand_id,
        topic=topic,
        limit=min(limit, 20),
    )

    return SearchResponse(stories=stories, total=len(stories))


@router.post("/stories/{entry_id}/extract", response_model=List[ExtractedStory])
async def extract_stories_endpoint(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Re-extract stories from an existing journal entry."""
    if not _UUID_RE.match(entry_id):
        raise HTTPException(400, "Invalid entry_id")

    from app.services.story_extractor import extract_and_save

    stories = await extract_and_save(entry_id, user.id)
    if not stories:
        return []

    return [ExtractedStory(**s) for s in stories]


@router.delete("/stories/{entry_id}", status_code=204)
async def delete_story(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a Story Bank entry."""
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
