"""Pydantic models for resource endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────


class ResourceCreateNote(BaseModel):
    """POST /resources (type=note or link)."""
    type: str = Field(..., pattern="^(note|link|transcript)$")
    title: str = Field(..., min_length=1, max_length=500)
    content_text: str = Field(default="", max_length=500000)
    source_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_gold: bool = False
    collection_id: Optional[str] = None
    brand_id: Optional[str] = None


class ResourceUpdate(BaseModel):
    """PATCH /resources/{id}."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    tags: Optional[List[str]] = None
    is_gold: Optional[bool] = None


# ── Response models ───────────────────────────────────────


class ResourceSummary(BaseModel):
    """Returned in list view (GET /resources)."""
    id: str
    type: str
    title: str
    source_url: Optional[str] = None
    tags: List[str]
    is_gold: bool
    storage_path: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChunkOut(BaseModel):
    """A single text chunk."""
    id: str
    chunk_index: int
    chunk_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResourceDetail(BaseModel):
    """Returned in detail view (GET /resources/{id})."""
    id: str
    type: str
    title: str
    source_url: Optional[str] = None
    tags: List[str]
    is_gold: bool
    content_text: str
    storage_path: Optional[str] = None
    chunks: List[ChunkOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResourceCreated(BaseModel):
    """Returned after POST /resources or POST /resources/upload."""
    id: str
    type: str
    title: str
    chunk_count: int
    message: str = "Resource created"


# ── Channel import models ────────────────────────────────


class ChannelImportRequest(BaseModel):
    """POST /resources/channel — bulk import from YouTube channel."""
    channel_url: str = Field(..., min_length=10)
    tags: List[str] = Field(default_factory=list)
    is_gold: bool = False
    max_videos: int = Field(default=50, ge=1, le=500)
    extract_transcripts: bool = Field(
        default=True,
        description="If true, extract transcripts for each video. If false, just import metadata.",
    )
    collection_id: Optional[str] = None
    brand_id: Optional[str] = None


class ChannelVideoSummary(BaseModel):
    """Summary of a single video from channel import."""
    video_id: str
    title: str
    views_str: str = ""
    duration_str: str = ""
    resource_id: Optional[str] = None
    status: str = "pending"  # pending, processing, success, failed, skipped


class ChannelImportResponse(BaseModel):
    """Returned after POST /resources/channel."""
    channel_name: str
    total_videos: int
    imported: int
    skipped: int
    failed: int
    videos: List[ChannelVideoSummary]
    message: str = ""
