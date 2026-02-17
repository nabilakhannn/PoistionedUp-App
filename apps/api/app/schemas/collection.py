"""Pydantic models for collection endpoints + Voice DNA."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Voice DNA model ─────────────────────────────────────


class VoiceDNA(BaseModel):
    """Structured writing style profile extracted from a creator's content."""
    tone: str = ""                            # "direct and aggressive" / "warm and conversational"
    sentence_style: str = ""                  # "short punchy" / "long flowing" / "mixed"
    vocabulary_level: str = ""                # "simple everyday" / "technical jargon" / "mixed"
    hook_patterns: List[str] = Field(default_factory=list)   # ["bold claims", "rhetorical questions"]
    cta_patterns: List[str] = Field(default_factory=list)    # ["direct ask", "soft nudge"]
    signature_phrases: List[str] = Field(default_factory=list)  # ["starving crowd", "dream outcome"]
    content_structure: str = ""               # "problem-solution-proof" / "story-lesson-action"
    personality_traits: List[str] = Field(default_factory=list)  # ["confident", "data-driven"]
    sample_hooks: List[str] = Field(default_factory=list)    # 5-10 representative hooks
    analysis_chunk_count: int = 0             # How many chunks were analyzed


# ── Request models ──────────────────────────────────────


class CollectionCreate(BaseModel):
    """POST /collections."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    creator_url: Optional[str] = None


class CollectionUpdate(BaseModel):
    """PATCH /collections/{id}."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    creator_url: Optional[str] = None


class CollectionAddResources(BaseModel):
    """POST /collections/{id}/resources — add existing resources."""
    resource_ids: List[str] = Field(..., min_length=1)


class CollectionSearchRequest(BaseModel):
    """POST /collections/{id}/search — semantic search within a collection."""
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


# ── Response models ─────────────────────────────────────


class CollectionSummary(BaseModel):
    """Returned in list view (GET /collections)."""
    id: str
    name: str
    description: str
    creator_url: Optional[str] = None
    resource_count: int = 0
    voice_dna_ready: bool = False
    created_at: datetime
    updated_at: datetime


class CollectionResourceOut(BaseModel):
    """Minimal resource info for collection detail view."""
    id: str
    type: str
    title: str
    source_url: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime


class CollectionDetail(BaseModel):
    """Returned in detail view (GET /collections/{id})."""
    id: str
    name: str
    description: str
    creator_url: Optional[str] = None
    voice_dna: VoiceDNA = Field(default_factory=VoiceDNA)
    resources: List[CollectionResourceOut] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CollectionSearchResult(BaseModel):
    """A single search result from collection-scoped search."""
    chunk_text: str
    resource_title: str = ""
    similarity: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollectionSearchResponse(BaseModel):
    """Returned from POST /collections/{id}/search."""
    collection_id: str
    collection_name: str
    query: str
    results: List[CollectionSearchResult] = Field(default_factory=list)


class VoiceDNAResponse(BaseModel):
    """Returned from POST /collections/{id}/analyze-voice."""
    collection_id: str
    collection_name: str
    voice_dna: VoiceDNA
    message: str = ""
