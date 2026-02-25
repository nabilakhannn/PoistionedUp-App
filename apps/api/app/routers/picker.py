"""Resource Picker: unified search across Knowledge resources and Inspo items.

Used by the chat interface to let users attach context from their library.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/picker", tags=["picker"])


# ── Response models ─────────────────────────────────────────


class PickerItem(BaseModel):
    """A single item in the picker search results."""

    id: str
    source: str = Field(..., description="'knowledge' or 'inspo'")
    title: str
    content_preview: str = Field(default="", description="First ~200 chars of content")
    tags: List[str] = Field(default_factory=list)
    is_gold: bool = False
    is_starred: bool = False
    source_tag: Optional[str] = None
    intent_note: Optional[str] = None
    resource_type: Optional[str] = None  # note, link, transcript, file, etc.
    content_type: Optional[str] = None  # text, link, image, video, voice_note
    source_url: Optional[str] = None
    board_name: Optional[str] = None  # For inspo items: which board they belong to
    created_at: str = ""


class PickerSearchResponse(BaseModel):
    """Response from the picker search endpoint."""

    items: List[PickerItem] = Field(default_factory=list)
    total: int = 0


class PickerContentResponse(BaseModel):
    """Full content of a picker item, formatted for LLM context injection."""

    id: str
    source: str
    title: str
    full_text: str
    is_gold: bool = False
    is_starred: bool = False
    source_tag: Optional[str] = None
    intent_note: Optional[str] = None
    formatted_context: str = Field(
        default="",
        description="Pre-formatted context string ready for LLM injection",
    )


# ── Search endpoint ─────────────────────────────────────────


@router.get("/search", response_model=PickerSearchResponse)
async def search_picker_items(
    q: Optional[str] = Query(None, description="Search query (matches title, content, tags)"),
    source: str = Query("all", pattern="^(all|knowledge|inspo)$", description="Filter by source type"),
    brand_id: Optional[UUID] = Query(None, description="Filter by brand ID"),
    gold_only: bool = Query(False, description="Show only gold resources"),
    starred_only: bool = Query(False, description="Show only starred inspo items"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    user: CurrentUser = Depends(get_current_user),
):
    """Search across Knowledge resources and Inspo items for the picker modal.

    Returns a unified list with preview data. Use /picker/content/{source}/{id}
    to fetch full content when attaching to chat.
    """
    admin = get_admin_client()
    items: List[PickerItem] = []

    # ── Knowledge resources ──────────────────────────────────
    if source in ("all", "knowledge"):
        knowledge_items = _search_knowledge(admin, user.id, q, brand_id, gold_only, limit)
        items.extend(knowledge_items)

    # ── Inspo items ──────────────────────────────────────────
    if source in ("all", "inspo"):
        inspo_items = _search_inspo(admin, user.id, q, brand_id, starred_only, limit)
        items.extend(inspo_items)

    # Sort by created_at desc across both sources
    items.sort(key=lambda x: x.created_at, reverse=True)

    # Apply overall limit
    items = items[:limit]

    return PickerSearchResponse(items=items, total=len(items))


# ── Content endpoint ─────────────────────────────────────────


@router.get("/content/{source}/{item_id}", response_model=PickerContentResponse)
async def get_picker_content(
    source: str,
    item_id: UUID,
    user: CurrentUser = Depends(get_current_user),
):
    """Fetch the full content of a Knowledge resource or Inspo item.

    Returns pre-formatted context string ready for LLM injection, including
    metadata like source_tag, intent_note, and gold status.
    """
    admin = get_admin_client()

    if source == "knowledge":
        return _get_knowledge_content(admin, item_id, user.id)
    elif source == "inspo":
        return _get_inspo_content(admin, item_id, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source must be 'knowledge' or 'inspo'",
        )


# ── Internal helpers ─────────────────────────────────────────


def _search_knowledge(
    admin: Any,
    user_id: str,
    q: Optional[str],
    brand_id: Optional[UUID],
    gold_only: bool,
    limit: int,
) -> List[PickerItem]:
    """Search knowledge resources."""
    query = (
        admin.table("resources")
        .select("id, type, title, source_url, tags, is_gold, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if brand_id:
        query = query.eq("brand_id", str(brand_id))

    if gold_only:
        query = query.eq("is_gold", True)

    resp = query.execute()

    items = []
    for r in (resp.data or []):
        title = r.get("title", "Untitled")
        # Text search filter (client-side for simplicity)
        if q:
            q_lower = q.lower()
            searchable = f"{title} {' '.join(r.get('tags', []))} {r.get('type', '')}".lower()
            if q_lower not in searchable:
                continue

        # Fetch a content preview from the first chunk
        preview = ""
        chunk_resp = (
            admin.table("resource_chunks")
            .select("chunk_text")
            .eq("resource_id", r["id"])
            .order("chunk_index")
            .limit(1)
            .execute()
        )
        if chunk_resp.data:
            full_text = chunk_resp.data[0].get("chunk_text", "")
            preview = full_text[:200] + ("..." if len(full_text) > 200 else "")

        items.append(
            PickerItem(
                id=r["id"],
                source="knowledge",
                title=title,
                content_preview=preview,
                tags=r.get("tags", []),
                is_gold=r.get("is_gold", False),
                is_starred=False,
                resource_type=r.get("type"),
                source_url=r.get("source_url"),
                created_at=r.get("created_at", ""),
            )
        )

    return items


def _search_inspo(
    admin: Any,
    user_id: str,
    q: Optional[str],
    brand_id: Optional[UUID],
    starred_only: bool,
    limit: int,
) -> List[PickerItem]:
    """Search inspo items across all boards."""
    # First get boards for this user (optionally filtered by brand)
    boards_query = (
        admin.table("inspo_boards")
        .select("id, name")
        .eq("user_id", user_id)
    )
    if brand_id:
        boards_query = boards_query.eq("brand_id", str(brand_id))

    boards_resp = boards_query.execute()
    if not boards_resp.data:
        return []

    board_map = {b["id"]: b["name"] for b in boards_resp.data}
    board_ids = list(board_map.keys())

    # Fetch items from those boards
    items_query = (
        admin.table("inspo_items")
        .select("id, board_id, content_type, content_text, source_url, source_tag, intent_note, tags, is_starred, created_at")
        .in_("board_id", board_ids)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if starred_only:
        items_query = items_query.eq("is_starred", True)

    items_resp = items_query.execute()

    items = []
    for item in (items_resp.data or []):
        content_text = item.get("content_text", "") or ""
        source_tag = item.get("source_tag", "") or ""
        intent_note = item.get("intent_note", "") or ""

        # Build a display title from content
        first_line = content_text.split("\n")[0][:80] if content_text else ""
        title = first_line or source_tag or f"{item.get('content_type', 'item')} item"

        # Text search filter
        if q:
            q_lower = q.lower()
            searchable = f"{content_text} {source_tag} {intent_note} {' '.join(item.get('tags', []))}".lower()
            if q_lower not in searchable:
                continue

        preview = content_text[:200] + ("..." if len(content_text) > 200 else "")

        items.append(
            PickerItem(
                id=item["id"],
                source="inspo",
                title=title,
                content_preview=preview,
                tags=item.get("tags", []),
                is_gold=False,
                is_starred=item.get("is_starred", False),
                source_tag=source_tag or None,
                intent_note=intent_note or None,
                content_type=item.get("content_type"),
                source_url=item.get("source_url"),
                board_name=board_map.get(item.get("board_id", ""), ""),
                created_at=item.get("created_at", ""),
            )
        )

    return items


def _get_knowledge_content(admin: Any, resource_id: UUID, user_id: str) -> PickerContentResponse:
    """Fetch full content of a knowledge resource with all chunks."""
    # Verify ownership
    res_resp = (
        admin.table("resources")
        .select("id, type, title, tags, is_gold, source_url, created_at")
        .eq("id", str(resource_id))
        .eq("user_id", user_id)
        .execute()
    )
    if not res_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    resource = res_resp.data[0]

    # Fetch all chunks
    chunks_resp = (
        admin.table("resource_chunks")
        .select("chunk_text")
        .eq("resource_id", str(resource_id))
        .order("chunk_index")
        .execute()
    )
    full_text = "\n\n".join(c["chunk_text"] for c in (chunks_resp.data or []))

    # Format for LLM context
    gold_marker = " [GOLD - HIGH PRIORITY]" if resource.get("is_gold") else ""
    formatted = (
        f"=== ATTACHED KNOWLEDGE RESOURCE{gold_marker} ===\n"
        f"Title: {resource.get('title', 'Untitled')}\n"
        f"Type: {resource.get('type', 'unknown')}\n"
    )
    if resource.get("tags"):
        formatted += f"Tags: {', '.join(resource['tags'])}\n"
    if resource.get("source_url"):
        formatted += f"Source: {resource['source_url']}\n"
    formatted += f"\n{full_text}\n=== END RESOURCE ==="

    return PickerContentResponse(
        id=resource["id"],
        source="knowledge",
        title=resource.get("title", "Untitled"),
        full_text=full_text,
        is_gold=resource.get("is_gold", False),
        formatted_context=formatted,
    )


def _get_inspo_content(admin: Any, item_id: UUID, user_id: str) -> PickerContentResponse:
    """Fetch full content of an inspo item."""
    item_resp = (
        admin.table("inspo_items")
        .select("id, board_id, content_type, content_text, source_url, source_tag, intent_note, tags, is_starred, created_at")
        .eq("id", str(item_id))
        .eq("user_id", user_id)
        .execute()
    )
    if not item_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspo item not found")

    item = item_resp.data[0]
    content_text = item.get("content_text", "") or ""
    source_tag = item.get("source_tag", "") or ""
    intent_note = item.get("intent_note", "") or ""

    # Get board name
    board_name = ""
    if item.get("board_id"):
        board_resp = (
            admin.table("inspo_boards")
            .select("name")
            .eq("id", item["board_id"])
            .execute()
        )
        if board_resp.data:
            board_name = board_resp.data[0].get("name", "")

    # Build display title
    first_line = content_text.split("\n")[0][:80] if content_text else ""
    title = first_line or source_tag or f"{item.get('content_type', 'item')} item"

    # Format for LLM context
    starred_marker = " [STARRED]" if item.get("is_starred") else ""
    formatted = f"=== ATTACHED INSPO ITEM{starred_marker} ===\n"
    if board_name:
        formatted += f"Board: {board_name}\n"
    formatted += f"Type: {item.get('content_type', 'unknown')}\n"
    if source_tag:
        formatted += f"Source: {source_tag}\n"
    if intent_note:
        formatted += (
            f"Intent (what the user wants the AI to derive from this): {intent_note}\n"
        )
    if item.get("tags"):
        formatted += f"Tags: {', '.join(item['tags'])}\n"
    if item.get("source_url"):
        formatted += f"URL: {item['source_url']}\n"
    formatted += f"\n{content_text}\n=== END INSPO ITEM ==="

    return PickerContentResponse(
        id=item["id"],
        source="inspo",
        title=title,
        full_text=content_text,
        is_starred=item.get("is_starred", False),
        source_tag=source_tag or None,
        intent_note=intent_note or None,
        formatted_context=formatted,
    )
