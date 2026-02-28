"""Pydantic schemas for the QA Review system.

Supports 6-dimension content quality scoring with strict thresholds:
  - Pass: score >= 80
  - Revise: score 50-79
  - Fail: score < 50
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Constants ─────────────────────────────────────────────────────

QA_PASS_THRESHOLD = 80
QA_REVISE_THRESHOLD = 50
QA_MAX_REVISIONS = 2

VALID_VERDICTS = {"pass", "revise", "fail", "pending"}
VALID_REF_TYPES = {"scheduled_item", "deliverable", "workflow", "freeform"}
VALID_PLATFORMS = {
    "linkedin", "twitter", "youtube", "tiktok", "instagram", "website", "other",
}
VALID_SEVERITIES = {"critical", "warning", "info"}
VALID_ISSUE_CATEGORIES = {"voice", "hook", "structure", "ai_tell", "virality", "goal"}

# Score dimension weights (must sum to 1.0)
SCORE_WEIGHTS = {
    "voice": 0.25,
    "hook": 0.20,
    "virality": 0.20,
    "ai_tell": 0.15,
    "structure": 0.10,
    "goal_alignment": 0.10,
}


# ── Request ───────────────────────────────────────────────────────

class QAReviewRequest(BaseModel):
    """Request to review a piece of content."""

    content_text: str = Field(..., min_length=1, max_length=50000)
    platform: Optional[str] = Field(None)
    content_ref_type: str = Field("freeform")
    content_ref_id: Optional[str] = Field(None)
    brand_id: Optional[str] = Field(None)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PLATFORMS:
            raise ValueError(f"Invalid platform: {v}. Must be one of {sorted(VALID_PLATFORMS)}")
        return v

    @field_validator("content_ref_type")
    @classmethod
    def validate_ref_type(cls, v: str) -> str:
        if v not in VALID_REF_TYPES:
            raise ValueError(f"Invalid ref type: {v}. Must be one of {sorted(VALID_REF_TYPES)}")
        return v


# ── Score Components ──────────────────────────────────────────────

class QAIssue(BaseModel):
    """A single quality issue found in the content."""

    category: str = Field(...)
    severity: str = Field("warning")
    detail: str = Field(...)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_ISSUE_CATEGORIES:
            raise ValueError(f"Invalid category: {v}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {v}")
        return v


class QARiskFlag(BaseModel):
    """A risk flag (medical claim, legal risk, etc.)."""

    type: str = Field(...)
    detail: str = Field(...)


class QAScoreBreakdown(BaseModel):
    """Individual dimension scores (0-100 each)."""

    voice_score: int = Field(0, ge=0, le=100)
    hook_score: int = Field(0, ge=0, le=100)
    structure_score: int = Field(0, ge=0, le=100)
    ai_tell_score: int = Field(0, ge=0, le=100)
    virality_score: int = Field(0, ge=0, le=100)
    goal_alignment_score: int = Field(0, ge=0, le=100)


# ── Result ────────────────────────────────────────────────────────

class QAReviewResult(BaseModel):
    """Full QA review result with scores, verdict, and feedback."""

    id: str
    overall_score: int = Field(..., ge=0, le=100)
    scores: QAScoreBreakdown
    verdict: str
    feedback: str
    issues: List[QAIssue] = Field(default_factory=list)
    risk_flags: List[QARiskFlag] = Field(default_factory=list)
    revision_number: int = Field(0, ge=0, le=5)
    revision_triggered: bool = False
    created_at: str

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        if v not in VALID_VERDICTS:
            raise ValueError(f"Invalid verdict: {v}. Must be one of {sorted(VALID_VERDICTS)}")
        return v


# ── Stats (Dashboard) ────────────────────────────────────────────

class QAStats(BaseModel):
    """Aggregated QA statistics for the dashboard."""

    total_reviews: int = 0
    pass_count: int = 0
    revise_count: int = 0
    fail_count: int = 0
    avg_score: float = 0.0
    avg_voice_score: float = 0.0
    avg_hook_score: float = 0.0
    avg_virality_score: float = 0.0
    common_issues: List[Dict[str, Any]] = Field(default_factory=list)


# ── Listing Model ────────────────────────────────────────────────

class QAReviewOut(BaseModel):
    """Lightweight listing model for the dashboard table."""

    id: str
    content_ref_type: str
    content_ref_id: Optional[str] = None
    platform: Optional[str] = None
    overall_score: int
    verdict: str
    feedback: Optional[str] = None
    revision_number: int = 0
    created_at: str
