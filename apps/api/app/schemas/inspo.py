"""Pydantic models for Inspo Boards endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────


class InspoBoardCreate(BaseModel):
    """POST /inspo/boards — create a new board."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    brand_id: Optional[str] = None


class InspoBoardUpdate(BaseModel):
    """PATCH /inspo/boards/{id} — update board name/description."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)


class InspoItemCreate(BaseModel):
    """POST /inspo/boards/{board_id}/items — add an item to a board."""
    content_type: str = Field(default="text", pattern="^(text|link|image|video|voice_note)$")
    title: str = Field(default="", max_length=500)
    content_text: str = Field(default="", max_length=500000)
    source_url: Optional[str] = None
    source_tag: str = Field(
        default="",
        max_length=500,
        description="Where this came from (e.g. 'Alex Hormozi, YouTube'). Auto-populated for links.",
    )
    intent_note: str = Field(
        default="",
        max_length=5000,
        description="Why you saved it and what the AI should derive from it.",
    )
    tags: List[str] = Field(default_factory=list)
    is_starred: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InspoItemUpdate(BaseModel):
    """PATCH /inspo/items/{id} — update an item."""
    title: Optional[str] = Field(None, max_length=500)
    content_text: Optional[str] = Field(None, max_length=500000)
    source_tag: Optional[str] = Field(None, max_length=500)
    intent_note: Optional[str] = Field(None, max_length=5000)
    tags: Optional[List[str]] = None
    is_starred: Optional[bool] = None
    sort_order: Optional[int] = None


# ── Response models ───────────────────────────────────────


class InspoBoardSummary(BaseModel):
    """Returned in list view (GET /inspo/boards)."""
    id: str
    name: str
    description: str = ""
    brand_id: Optional[str] = None
    item_count: int = 0
    starred_count: int = 0
    created_at: datetime
    updated_at: datetime


class InspoItemSummary(BaseModel):
    """An item within a board."""
    id: str
    board_id: str
    content_type: str
    title: str = ""
    content_text: str = ""
    source_url: Optional[str] = None
    source_tag: str = ""
    intent_note: str = ""
    media_path: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_starred: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class InspoBoardDetail(BaseModel):
    """Returned in detail view (GET /inspo/boards/{id})."""
    id: str
    name: str
    description: str = ""
    brand_id: Optional[str] = None
    items: List[InspoItemSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InspoItemCreated(BaseModel):
    """Returned after POST /inspo/boards/{board_id}/items."""
    id: str
    content_type: str
    title: str
    source_tag: str = ""
    message: str = "Item added to board"


# Alias used by the router for full item responses
InspoItemDetail = InspoItemSummary
