"""Inspo Boards router: CRUD for boards and items.

Boards hold multi-format inspiration items (text, links, images, videos,
voice notes). Items carry a source_tag and intent_note so the AI agent
knows what to derive from each piece of saved content.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.services.analytics import track_event
from app.schemas.inspo import (
    InspoBoardCreate,
    InspoBoardDetail,
    InspoBoardSummary,
    InspoBoardUpdate,
    InspoItemCreate,
    InspoItemDetail,
    InspoItemUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspo", tags=["inspo"])

MAX_BOARDS_PER_USER = 50
MAX_ITEMS_PER_BOARD = 500


# ── Helpers ──────────────────────────────────────────────


def _get_board_or_404(admin, board_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch a board row owned by user or raise 404."""
    resp = (
        admin.table("inspo_boards")
        .select("*")
        .eq("id", board_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        )
    return resp.data[0]


def _get_item_or_404(admin, item_id: str, user_id: str) -> Dict[str, Any]:
    """Fetch an item row owned by user or raise 404."""
    resp = (
        admin.table("inspo_items")
        .select("*")
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return resp.data[0]


def _count_board_items(admin, board_id: str) -> int:
    """Count items in a board."""
    resp = (
        admin.table("inspo_items")
        .select("id", count="exact")
        .eq("board_id", board_id)
        .execute()
    )
    return len(resp.data) if resp.data else 0


def _auto_source_tag(url: str) -> str:
    """Generate a source tag from a URL by detecting the platform."""
    try:
        from app.services.ingestion import detect_platform
        platform = detect_platform(url)
        platform_labels = {
            "youtube_video": "YouTube",
            "youtube_channel": "YouTube Channel",
            "tiktok": "TikTok",
            "facebook": "Facebook",
            "reddit": "Reddit",
            "twitter": "Twitter/X",
            "substack": "Substack",
            "linkedin": "LinkedIn",
            "webpage": "Website",
        }
        return platform_labels.get(platform, "Website")
    except Exception:
        return "Website"


def _extract_link_content(url: str) -> Dict[str, Any]:
    """Extract text content and metadata from a URL for an inspo item.

    Returns dict with 'content_text', 'source_tag', 'metadata'.
    Degrades gracefully if extraction fails.
    """
    result = {
        "content_text": "",
        "source_tag": _auto_source_tag(url),
        "metadata": {},
    }

    try:
        from app.services.ingestion import extract_text_from_url

        extracted = extract_text_from_url(url)
        if extracted.get("text"):
            # Limit to 100K chars for inspo items
            result["content_text"] = extracted["text"][:100000]
        if extracted.get("metadata"):
            result["metadata"] = extracted["metadata"]
        if extracted.get("source_type"):
            result["metadata"]["source_type"] = extracted["source_type"]
        if extracted.get("error"):
            result["metadata"]["extraction_error"] = extracted["error"]
    except Exception as exc:
        logger.warning("Link extraction failed for %s: %s", url, exc)
        result["metadata"]["extraction_error"] = str(exc)[:200]

    return result


# ── Board CRUD ───────────────────────────────────────────


@router.get("/boards", response_model=List[InspoBoardSummary])
async def list_boards(
    brand_id: Optional[str] = Query(None, description="Filter by brand"),
    user: CurrentUser = Depends(get_current_user),
):
    """List all inspo boards for the current user."""
    admin = get_admin_client()

    query = (
        admin.table("inspo_boards")
        .select("*")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
    )

    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    boards = resp.data or []

    # Attach item counts
    results = []
    for board in boards:
        count = _count_board_items(admin, board["id"])
        results.append(InspoBoardSummary(
            id=board["id"],
            user_id=board["user_id"],
            brand_id=board.get("brand_id"),
            name=board["name"],
            description=board.get("description"),
            item_count=count,
            created_at=board["created_at"],
            updated_at=board["updated_at"],
        ))

    return results


@router.post("/boards", response_model=InspoBoardSummary, status_code=status.HTTP_201_CREATED)
async def create_board(
    body: InspoBoardCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new inspo board."""
    admin = get_admin_client()

    # Check board limit
    existing = (
        admin.table("inspo_boards")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .execute()
    )
    if len(existing.data or []) >= MAX_BOARDS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BOARDS_PER_USER} boards allowed per user",
        )

    row = {
        "user_id": user.id,
        "name": body.name,
        "description": body.description,
    }
    if body.brand_id:
        row["brand_id"] = str(body.brand_id)

    resp = admin.table("inspo_boards").insert(row).execute()
    board = resp.data[0]

    track_event(user.id, "inspo_board_created", {
        "board_id": board["id"],
        "brand_id": body.brand_id or "",
    })

    return InspoBoardSummary(
        id=board["id"],
        user_id=board["user_id"],
        brand_id=board.get("brand_id"),
        name=board["name"],
        description=board.get("description"),
        item_count=0,
        created_at=board["created_at"],
        updated_at=board["updated_at"],
    )


@router.get("/boards/{board_id}", response_model=InspoBoardDetail)
async def get_board(
    board_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single inspo board with all its items."""
    admin = get_admin_client()
    board = _get_board_or_404(admin, board_id, user.id)

    # Fetch items
    items_resp = (
        admin.table("inspo_items")
        .select("*")
        .eq("board_id", board_id)
        .order("created_at", desc=True)
        .execute()
    )
    items = [InspoItemDetail(**item) for item in (items_resp.data or [])]

    return InspoBoardDetail(
        id=board["id"],
        user_id=board["user_id"],
        brand_id=board.get("brand_id"),
        name=board["name"],
        description=board.get("description"),
        item_count=len(items),
        created_at=board["created_at"],
        updated_at=board["updated_at"],
        items=items,
    )


@router.patch("/boards/{board_id}", response_model=InspoBoardSummary)
async def update_board(
    board_id: str,
    body: InspoBoardUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update an inspo board's name, description, or brand association."""
    admin = get_admin_client()
    _get_board_or_404(admin, board_id, user.id)

    updates = body.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Convert brand_id to string if present
    if "brand_id" in updates and updates["brand_id"] is not None:
        updates["brand_id"] = str(updates["brand_id"])

    resp = (
        admin.table("inspo_boards")
        .update(updates)
        .eq("id", board_id)
        .eq("user_id", user.id)
        .execute()
    )
    board = resp.data[0]
    count = _count_board_items(admin, board_id)

    return InspoBoardSummary(
        id=board["id"],
        user_id=board["user_id"],
        brand_id=board.get("brand_id"),
        name=board["name"],
        description=board.get("description"),
        item_count=count,
        created_at=board["created_at"],
        updated_at=board["updated_at"],
    )


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete an inspo board and all its items (cascade)."""
    admin = get_admin_client()
    _get_board_or_404(admin, board_id, user.id)

    admin.table("inspo_boards").delete().eq("id", board_id).eq("user_id", user.id).execute()
    return None


# ── Item CRUD ────────────────────────────────────────────


@router.get("/boards/{board_id}/items", response_model=List[InspoItemDetail])
async def list_items(
    board_id: str,
    starred_only: bool = Query(False, description="Only show starred items"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    user: CurrentUser = Depends(get_current_user),
):
    """List items in a board with optional filters."""
    admin = get_admin_client()
    _get_board_or_404(admin, board_id, user.id)

    query = (
        admin.table("inspo_items")
        .select("*")
        .eq("board_id", board_id)
        .order("created_at", desc=True)
    )

    if starred_only:
        query = query.eq("is_starred", True)

    if tag:
        query = query.contains("tags", [tag])

    resp = query.execute()
    return [InspoItemDetail(**item) for item in (resp.data or [])]


@router.post("/boards/{board_id}/items", response_model=InspoItemDetail, status_code=status.HTTP_201_CREATED)
async def create_item(
    board_id: str,
    body: InspoItemCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Add a new item to a board.

    For link-type items, the system automatically:
    - Detects the platform (YouTube, Reddit, Twitter, etc.)
    - Extracts text content from the URL
    - Sets source_tag if not provided by the user
    """
    admin = get_admin_client()
    _get_board_or_404(admin, board_id, user.id)

    # Check item limit
    count = _count_board_items(admin, board_id)
    if count >= MAX_ITEMS_PER_BOARD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ITEMS_PER_BOARD} items per board",
        )

    row = {
        "board_id": board_id,
        "user_id": user.id,
        "content_type": body.content_type,
        "content_text": body.content_text,
        "source_url": body.source_url,
        "source_tag": body.source_tag,
        "intent_note": body.intent_note,
        "tags": body.tags,
        "is_starred": body.is_starred,
        "metadata": body.metadata,
    }

    # Auto-extract for link items
    if body.content_type == "link" and body.source_url:
        extracted = _extract_link_content(body.source_url)

        # Only fill in content_text if user did not supply their own
        if not row["content_text"]:
            row["content_text"] = extracted["content_text"]

        # Auto-set source_tag if user did not supply one
        if not row["source_tag"]:
            row["source_tag"] = extracted["source_tag"]

        # Merge extraction metadata with user-provided metadata
        merged_meta = extracted.get("metadata", {})
        merged_meta.update(body.metadata)
        row["metadata"] = merged_meta

    resp = admin.table("inspo_items").insert(row).execute()
    item = resp.data[0]

    track_event(user.id, "inspo_item_created", {
        "item_id": item["id"],
        "board_id": board_id,
        "content_type": body.content_type,
    })

    return InspoItemDetail(**item)


@router.get("/items/{item_id}", response_model=InspoItemDetail)
async def get_item(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single inspo item."""
    admin = get_admin_client()
    item = _get_item_or_404(admin, item_id, user.id)
    return InspoItemDetail(**item)


@router.patch("/items/{item_id}", response_model=InspoItemDetail)
async def update_item(
    item_id: str,
    body: InspoItemUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update an inspo item's fields."""
    admin = get_admin_client()
    _get_item_or_404(admin, item_id, user.id)

    updates = body.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    resp = (
        admin.table("inspo_items")
        .update(updates)
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    return InspoItemDetail(**resp.data[0])


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete an inspo item."""
    admin = get_admin_client()
    _get_item_or_404(admin, item_id, user.id)

    admin.table("inspo_items").delete().eq("id", item_id).eq("user_id", user.id).execute()

    track_event(user.id, "inspo_item_deleted", {"item_id": item_id})

    return None


@router.patch("/items/{item_id}/star", response_model=InspoItemDetail)
async def toggle_star(
    item_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Toggle the starred status of an inspo item."""
    admin = get_admin_client()
    item = _get_item_or_404(admin, item_id, user.id)

    new_starred = not item.get("is_starred", False)

    resp = (
        admin.table("inspo_items")
        .update({"is_starred": new_starred})
        .eq("id", item_id)
        .eq("user_id", user.id)
        .execute()
    )
    return InspoItemDetail(**resp.data[0])
