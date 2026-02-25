"""Pydantic models for the Agent Training system.

Covers:
  - Admin: prompt config CRUD, training examples CRUD, feedback review
  - User: feedback submission, custom instructions
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Admin: Prompt Config ──────────────────────────────────────


class PromptConfigOut(BaseModel):
    """A single prompt configuration section."""

    id: str
    config_type: str
    config_key: str
    content: str
    version: int = 1
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PromptConfigUpdate(BaseModel):
    """Update a prompt config section."""

    content: str = Field(..., min_length=1, max_length=50000)
    metadata: Optional[Dict[str, Any]] = None


# ── Admin: Training Examples ──────────────────────────────────


class TrainingExampleCreate(BaseModel):
    """Create a new training example."""

    category: str = Field(
        ...,
        pattern="^(good_response|bad_response|pushback|field_question|voice_example)$",
    )
    module: Optional[str] = None
    field: Optional[str] = None
    user_input: str = Field(default="", max_length=5000)
    ideal_response: str = Field(default="", max_length=10000)
    context_notes: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default_factory=list)


class TrainingExampleUpdate(BaseModel):
    """Update an existing training example."""

    category: Optional[str] = Field(
        None,
        pattern="^(good_response|bad_response|pushback|field_question|voice_example)$",
    )
    module: Optional[str] = None
    field: Optional[str] = None
    user_input: Optional[str] = Field(None, max_length=5000)
    ideal_response: Optional[str] = Field(None, max_length=10000)
    context_notes: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TrainingExampleOut(BaseModel):
    """A training example."""

    id: str
    category: str
    module: Optional[str] = None
    field: Optional[str] = None
    user_input: str = ""
    ideal_response: str = ""
    context_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── User: Feedback ────────────────────────────────────────────


class FeedbackCreate(BaseModel):
    """Submit feedback on an AI response."""

    brand_id: str
    chat_id: Optional[str] = None
    message_index: Optional[int] = None
    feedback_type: str = Field(
        ...,
        pattern="^(thumbs_up|thumbs_down|correction|voice_mismatch)$",
    )
    feedback_text: Optional[str] = Field(None, max_length=2000)
    original_response: str = Field(default="", max_length=10000)
    response_metadata: Optional[Dict[str, Any]] = None


class FeedbackOut(BaseModel):
    """A feedback entry."""

    id: str
    user_id: str
    brand_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_index: Optional[int] = None
    feedback_type: str
    feedback_text: Optional[str] = None
    original_response: str = ""
    response_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class FeedbackSummary(BaseModel):
    """Aggregated feedback statistics."""

    total_feedback: int = 0
    thumbs_up: int = 0
    thumbs_down: int = 0
    corrections: int = 0
    voice_mismatches: int = 0
    recent_feedback: List[FeedbackOut] = Field(default_factory=list)


# ── User: Custom Instructions ─────────────────────────────────


class CustomInstructionsUpsert(BaseModel):
    """Create or update custom instructions for a brand."""

    instructions: str = Field(default="", max_length=5000)
    tone_preference: Optional[str] = Field(None, max_length=200)
    avoid_topics: List[str] = Field(default_factory=list)
    focus_areas: List[str] = Field(default_factory=list)


class CustomInstructionsOut(BaseModel):
    """Custom instructions for a brand."""

    id: str
    user_id: str
    brand_id: Optional[str] = None
    instructions: str = ""
    tone_preference: Optional[str] = None
    avoid_topics: List[str] = Field(default_factory=list)
    focus_areas: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Admin: Training Stats ─────────────────────────────────────


class TrainingStats(BaseModel):
    """Overview statistics for admin dashboard."""

    total_configs: int = 0
    total_examples: int = 0
    total_feedback: int = 0
    feedback_by_type: Dict[str, int] = Field(default_factory=dict)
    recent_corrections: List[FeedbackOut] = Field(default_factory=list)
