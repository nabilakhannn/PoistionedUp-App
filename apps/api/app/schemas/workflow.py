"""Pydantic models for workflow endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Valid platforms ────────────────────────────────────────

VALID_PLATFORMS = ["youtube", "linkedin", "twitter", "short_form"]


# ── Request models ────────────────────────────────────────


class WorkflowCreate(BaseModel):
    """POST /workflows request body."""
    goal_text: str = Field(
        ..., min_length=10, max_length=2000,
        description="What the user wants the content to be about",
    )
    platforms: List[str] = Field(
        default_factory=lambda: ["youtube"],
        description="Target platforms: youtube, linkedin, twitter, short_form",
    )
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "sources": {
                "youtube": True,
                "reddit": True,
                "twitter": False,
                "tiktok": False,
                "instagram": False,
                "newsletters": True,
                "news": True,
                "competitor_channels": [],
                "user_resources": True,
            }
        },
        description="Research source toggles and other settings",
    )
    brand_id: Optional[str] = Field(
        None,
        description="ID of the personal brand to use for content generation. "
                    "If omitted, uses the user's current/default brand.",
    )


# ── Response models ───────────────────────────────────────


class WorkflowSummary(BaseModel):
    """Returned in list view (GET /workflows)."""
    id: str
    status: str
    goal_text: str
    current_step: Optional[str] = None
    active_version: int
    created_at: datetime
    updated_at: datetime
    platforms: List[str] = Field(default_factory=lambda: ["youtube"])
    estimated_cost: float = 0.0
    objective: Optional[str] = None
    content_type: Optional[str] = None


class WorkflowDetail(BaseModel):
    """Returned in detail view (GET /workflows/{id})."""
    id: str
    status: str
    goal_text: str
    settings: Dict[str, Any]
    profile_snapshot: Dict[str, Any]
    workflow_plan: Optional[Dict[str, Any]] = None
    current_step: Optional[str] = None
    active_version: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    platforms: List[str] = Field(default_factory=lambda: ["youtube"])


class WorkflowCreated(BaseModel):
    """Returned after POST /workflows."""
    id: str
    status: str
    message: str = "Workflow created and queued"


class ContentAsset(BaseModel):
    """A single content asset from a workflow."""
    id: str
    workflow_id: str
    type: str
    platform: str = "youtube"
    content_json: Optional[Dict[str, Any]] = None
    version: int = 1
    is_latest: bool = True
    status: str = "draft"
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
