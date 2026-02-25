"""Pydantic schemas for the Agent Memory system."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# -- Create / Update ────────────────────────────────────────

class AgentMemoryCreate(BaseModel):
    """Create a new agent memory."""
    memory_type: str = Field(..., min_length=1)      # observation, preference, lesson, content_pattern, voice_note
    content: str = Field(..., min_length=1)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    platform: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None                     # auto, user_edit, metrics, synthesis
    related_post_ids: Optional[List[str]] = None
    status: Optional[str] = None                     # defaults to 'active' in DB
    brand_id: Optional[str] = None


class AgentMemoryUpdate(BaseModel):
    """Update an existing memory's content or metadata."""
    content: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    platform: Optional[str] = None
    category: Optional[str] = None


# -- Response Models ────────────────────────────────────────

class AgentMemorySummary(BaseModel):
    """Compact memory listing."""
    id: str
    memory_type: str
    content: str
    confidence: float
    status: str
    platform: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    brand_id: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: str


class AgentMemoryDetail(BaseModel):
    """Full memory detail with evidence and relationships."""
    id: str
    memory_type: str
    content: str
    confidence: float
    status: str
    platform: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    evidence: List[Any] = []
    related_post_ids: List[str] = []
    supersedes_id: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: str
    updated_at: str


# -- Action Models ──────────────────────────────────────────

class MemoryApprovalAction(BaseModel):
    """Approve or dismiss a pending memory."""
    action: str = Field(..., pattern="^(approve|dismiss)$")
    edited_content: Optional[str] = None  # If user wants to edit before approving


class MemorySynthesisResponse(BaseModel):
    """Result of synthesizing/consolidating memories."""
    new_memories_created: int
    memories_superseded: int
    patterns_detected: List[str] = []
    message: str
