"""Pydantic models for the Brand Strategist v2 response types.

These map directly to the JSON response format defined in the
PositionedUp System Prompt v2.

Response Types:
  - options: Question with 2-3 option cards
  - refinement: Refining a selected/custom answer
  - save: Confirming a field save
  - message: General coaching message
  - content: Delivering created content
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ── Option Card ───────────────────────────────────────────────


class OptionCard(BaseModel):
    """A single option presented to the user."""

    id: str = Field(..., description="Option identifier: A, B, or C")
    label: str = Field(..., description="Short strategic label (2-5 words)")
    text: str = Field(..., description="The full drafted answer (1-3 sentences)")


class CompletenessInfo(BaseModel):
    """Completeness percentages returned after a save."""

    module_name: str
    module_percent: int = 0
    overall_percent: int = 0


# ── Response Types ────────────────────────────────────────────


class OptionsResponse(BaseModel):
    """Type 1: Asking a question with option cards."""

    type: str = "options"
    module: str
    field: str
    message: str = Field(..., description="Coaching question in direct voice")
    options: List[OptionCard] = Field(
        default_factory=list,
        description="2-3 option cards (empty for first question when zero context)",
    )
    allow_custom: bool = True
    allow_skip: bool = True


class RefinementResponse(BaseModel):
    """Type 2: Refining a selected or custom answer."""

    type: str = "refinement"
    module: str
    field: str
    message: str = Field(..., description="Coaching response acknowledging choice")
    refined_text: str = Field(..., description="Polished answer ready to save")
    actions: List[str] = Field(
        default_factory=lambda: ["confirm", "edit"],
    )


class SaveResponse(BaseModel):
    """Type 3: Confirming a save to a module field."""

    type: str = "save"
    module: str
    field: str
    value: Any = Field(..., description="The confirmed answer being saved")
    message: str = Field(..., description="Brief confirmation + transition")
    completeness: Optional[CompletenessInfo] = None


class MessageResponse(BaseModel):
    """Type 4: General coaching message (no options, no save)."""

    type: str = "message"
    message: str = Field(..., description="Coaching message, can be multi-paragraph")


class ContentResponse(BaseModel):
    """Type 5: Delivering created content."""

    type: str = "content"
    content_type: str = Field(..., description="e.g., linkedin_post, youtube_script")
    platform: str
    pillar: Optional[str] = None
    hook: str
    body: str
    cta: Optional[str] = None
    message: str = Field(..., description="Brief coaching note about the content")


# ── Union type for parsing ────────────────────────────────────

StrategistResponse = Union[
    OptionsResponse,
    RefinementResponse,
    SaveResponse,
    MessageResponse,
    ContentResponse,
]


# ── Request types ─────────────────────────────────────────────


class StrategistChatRequest(BaseModel):
    """POST /brand/strategist/chat request body."""

    message: str = Field(..., min_length=1, max_length=5000)
    brand_id: str = Field(..., description="Personal brand ID")
    selected_option: Optional[str] = Field(
        None,
        description="If user selected an option (A, B, C), its id",
    )
    action: Optional[str] = Field(
        None,
        pattern="^(confirm|edit|skip|custom)$",
        description="User action on a refinement or option",
    )
    target_field: Optional[str] = Field(
        None,
        description="The module.field this message relates to (for context)",
    )
    file_context: Optional[str] = Field(
        None,
        max_length=20000,
        description="Extracted text from an uploaded file",
    )
    file_name: Optional[str] = Field(None, max_length=255)
    attachment_type: Optional[str] = Field(
        None,
        pattern="^(file|link|knowledge|inspo)$",
    )


class StrategistChatResponse(BaseModel):
    """POST /brand/strategist/chat response body."""

    responses: List[Dict[str, Any]] = Field(
        ...,
        description="Array of response objects (options, save, message, etc.)",
    )
    completeness: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current field-level completeness state",
    )
    chat_id: str
    history: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Full conversation history (returned on resume/new, not on chat)",
    )


class FieldCompletenessResponse(BaseModel):
    """GET /brand/strategist/completeness response."""

    overall_percent: int = 0
    overall_filled: int = 0
    overall_total: int = 0
    modules: Dict[str, Any] = Field(default_factory=dict)
    filled_fields: List[str] = Field(default_factory=list)
    unfilled_fields: List[str] = Field(default_factory=list)


class NextFieldResponse(BaseModel):
    """GET /brand/strategist/next-field response."""

    module: Optional[str] = None
    field: Optional[str] = None
    label: Optional[str] = None
    question: Optional[str] = None
    all_complete: bool = False
