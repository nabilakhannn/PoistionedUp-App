"""Pydantic schemas for the Competitor Intelligence system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_PLATFORMS = {
    "linkedin", "twitter", "youtube", "tiktok", "instagram", "website", "other",
}

VALID_CONTENT_FORMATS = {
    "post", "video", "carousel", "thread", "story", "article", "other",
}


# ── Create / Update ────────────────────────────────────────────

class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    platform: str = Field("website")
    profile_url: str = Field(..., min_length=1, max_length=2000)
    positioning: Optional[str] = Field(None, max_length=1000)
    niche: Optional[str] = Field(None, max_length=200)
    pricing_tier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=5000)
    threat_level: int = Field(3, ge=1, le=5)
    brand_id: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in VALID_PLATFORMS:
            raise ValueError(f"Invalid platform: {v}. Valid: {sorted(VALID_PLATFORMS)}")
        return v


class CompetitorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    platform: Optional[str] = None
    profile_url: Optional[str] = Field(None, min_length=1, max_length=2000)
    positioning: Optional[str] = Field(None, max_length=1000)
    niche: Optional[str] = Field(None, max_length=200)
    pricing_tier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=5000)
    threat_level: Optional[int] = Field(None, ge=1, le=5)
    brand_id: Optional[str] = None
    status: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PLATFORMS:
            raise ValueError(f"Invalid platform: {v}. Valid: {sorted(VALID_PLATFORMS)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "archived"):
            raise ValueError("status must be 'active' or 'archived'")
        return v


# ── Output ──────────────────────────────────────────────────────

class CompetitorMetricSnapshot(BaseModel):
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    post_frequency_weekly: Optional[float] = None
    avg_post_engagement: Optional[int] = None
    top_topic: Optional[str] = None


class CompetitorOut(BaseModel):
    id: str
    user_id: str
    brand_id: Optional[str] = None
    name: str
    platform: str
    profile_url: str
    positioning: Optional[str] = None
    niche: Optional[str] = None
    estimated_followers: Optional[int] = None
    pricing_tier: Optional[str] = None
    notes: Optional[str] = None
    threat_level: int = 3
    threat_level_override: bool = False
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_metrics: Optional[CompetitorMetricSnapshot] = None


# ── Metrics ─────────────────────────────────────────────────────

class CompetitorMetricRecord(BaseModel):
    followers: Optional[int] = None
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    post_frequency_weekly: Optional[float] = Field(None, ge=0)
    avg_post_engagement: Optional[int] = Field(None, ge=0)
    top_topic: Optional[str] = Field(None, max_length=200)
    source: str = Field("manual")


class CompetitorMetricOut(CompetitorMetricRecord):
    id: str
    competitor_id: str
    recorded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ── Content ─────────────────────────────────────────────────────

class CompetitorContentRecord(BaseModel):
    published_at: Optional[datetime] = None
    platform: Optional[str] = None
    title: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, max_length=2000)
    content_preview: Optional[str] = Field(None, max_length=5000)
    topics: List[str] = Field(default_factory=list)
    engagement_count: Optional[int] = Field(None, ge=0)
    engagement_rate: Optional[float] = Field(None, ge=0)
    format: str = Field("post")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in VALID_CONTENT_FORMATS:
            raise ValueError(f"Invalid format: {v}. Valid: {sorted(VALID_CONTENT_FORMATS)}")
        return v


class CompetitorContentOut(CompetitorContentRecord):
    id: str
    competitor_id: str
    created_at: Optional[datetime] = None


# ── Comparison & Analysis ───────────────────────────────────────

class CompetitorComparison(BaseModel):
    competitor_id: str
    competitor_name: str
    user_metrics: Dict[str, Any] = Field(default_factory=dict)
    competitor_metrics: Dict[str, Any] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)


class CompetitorAnalysisReport(BaseModel):
    competitor_id: str
    summary: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    content_pillars: List[str] = Field(default_factory=list)
    threat_assessment: str = ""


class ContentGap(BaseModel):
    topic: str
    covered_by_competitors: List[str] = Field(default_factory=list)
    your_coverage: bool = False
    priority: str = "medium"


class ContentGapAnalysis(BaseModel):
    gaps: List[ContentGap] = Field(default_factory=list)
    your_unique_topics: List[str] = Field(default_factory=list)
    shared_topics: List[str] = Field(default_factory=list)


# ── Threat Scoring ────────────────────────────────────────────

VALID_ALERT_TYPES = {
    "follower_surge", "engagement_drop", "positioning_shift",
    "content_spike", "new_strategy",
}

VALID_ALERT_SEVERITIES = {"low", "medium", "high"}

# Threat scoring weights (must sum to 1.0)
THREAT_WEIGHTS = {
    "engagement_growth": 0.30,
    "content_overlap": 0.25,
    "frequency": 0.25,
    "follower_ratio": 0.20,
}


class ThreatScoreDetail(BaseModel):
    """Dynamic threat score calculation breakdown."""
    calculated_score: float = Field(..., ge=1.0, le=5.0)
    engagement_growth_factor: float = 0.0
    content_overlap_factor: float = 0.0
    frequency_factor: float = 0.0
    follower_ratio_factor: float = 0.0
    reasoning: str = ""
    is_overridden: bool = False


class CompetitorAlert(BaseModel):
    """A competitor intelligence alert."""
    id: Optional[str] = None
    competitor_id: str
    competitor_name: str
    alert_type: str
    detail: str
    metric_before: Optional[float] = None
    metric_after: Optional[float] = None
    severity: str = "medium"
    created_at: Optional[str] = None

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in VALID_ALERT_TYPES:
            raise ValueError(f"Invalid alert_type: {v}. Valid: {sorted(VALID_ALERT_TYPES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in VALID_ALERT_SEVERITIES:
            raise ValueError(f"Invalid severity: {v}. Valid: {sorted(VALID_ALERT_SEVERITIES)}")
        return v


# ── Intelligence Feed ─────────────────────────────────────────

class IntelligenceFeedItem(BaseModel):
    """Single item in the intelligence feed."""
    item_type: str  # "analysis" | "alert"
    competitor_id: str
    competitor_name: str
    summary: str
    threat_level: Optional[int] = None
    date: Optional[str] = None


class IntelligenceFeed(BaseModel):
    """Aggregated competitor intelligence for the feed page."""
    active_competitors: int = 0
    avg_threat_level: float = 0.0
    latest_analysis_date: Optional[str] = None
    open_alerts: int = 0
    recent_analyses: List[IntelligenceFeedItem] = Field(default_factory=list)
    recent_alerts: List[CompetitorAlert] = Field(default_factory=list)
    benchmarks: Dict[str, Any] = Field(default_factory=dict)
