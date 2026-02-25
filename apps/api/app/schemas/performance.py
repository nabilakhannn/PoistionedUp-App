"""Pydantic schemas for the Performance Feedback system."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Create / Update ─────────────────────────────────────────

class ContentPostCreate(BaseModel):
    """Log a published piece of content."""
    title: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1)     # youtube_long, linkedin_post, etc.
    platform: str = Field(..., min_length=1)          # youtube, linkedin, instagram, etc.
    hook_used: Optional[str] = None
    hook_type: Optional[str] = None                   # question, bold_claim, story, statistic, contrarian
    topic: Optional[str] = None
    topic_category: Optional[str] = None              # ai_tools, business_strategy, etc.
    content_body: Optional[str] = None
    workflow_id: Optional[str] = None
    collection_id: Optional[str] = None
    published_url: Optional[str] = None
    published_at: Optional[str] = None                # ISO datetime string
    day_of_week: Optional[str] = None
    tags: Optional[List[str]] = None
    brand_id: Optional[str] = None


class ContentPostUpdateMetrics(BaseModel):
    """Update metrics for an existing post (can be partial)."""
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    watch_time_seconds: Optional[int] = None
    click_through_rate: Optional[float] = None
    impressions: Optional[int] = None
    reach: Optional[int] = None
    subscribers_gained: Optional[int] = None


# ── Response Models ─────────────────────────────────────────

class ContentPostSummary(BaseModel):
    """Compact post listing."""
    id: str
    title: str
    content_type: str
    platform: str
    hook_type: Optional[str] = None
    topic: Optional[str] = None
    topic_category: Optional[str] = None
    performance_tier: Optional[str] = None
    engagement_rate: Optional[float] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    published_at: Optional[str] = None
    created_at: str


class ContentPostDetail(BaseModel):
    """Full post detail including all metrics and AI analysis."""
    id: str
    title: str
    content_type: str
    platform: str
    hook_used: Optional[str] = None
    hook_type: Optional[str] = None
    topic: Optional[str] = None
    topic_category: Optional[str] = None
    content_body: Optional[str] = None
    workflow_id: Optional[str] = None
    collection_id: Optional[str] = None
    published_url: Optional[str] = None
    published_at: Optional[str] = None
    day_of_week: Optional[str] = None
    # Metrics
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    watch_time_seconds: Optional[int] = None
    click_through_rate: Optional[float] = None
    impressions: Optional[int] = None
    reach: Optional[int] = None
    subscribers_gained: Optional[int] = None
    # Calculated
    engagement_rate: Optional[float] = None
    performance_tier: Optional[str] = None
    # AI
    agent_analysis: Dict[str, Any] = {}
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: str
    updated_at: str


class PostAnalysisResponse(BaseModel):
    """AI analysis of why a post performed well or poorly."""
    post_id: str
    performance_tier: Optional[str] = None
    analysis: Dict[str, Any] = {}
    message: str


# ── Analytics Models ────────────────────────────────────────

class PlatformBreakdown(BaseModel):
    """Metrics aggregated by platform."""
    platform: str
    post_count: int
    avg_engagement_rate: Optional[float] = None
    avg_views: Optional[float] = None
    top_tier_count: int = 0          # viral + above_average


class TopicBreakdown(BaseModel):
    """Performance by topic category."""
    topic_category: str
    post_count: int
    avg_engagement_rate: Optional[float] = None
    avg_views: Optional[float] = None


class HookBreakdown(BaseModel):
    """Performance by hook type."""
    hook_type: str
    post_count: int
    avg_engagement_rate: Optional[float] = None
    example_hooks: List[str] = []


class PatternDetected(BaseModel):
    """An auto-detected performance pattern."""
    pattern: str               # Human-readable description
    evidence: str              # What data supports this
    confidence: float = 0.5    # 0-1 how confident


class PerformanceAnalytics(BaseModel):
    """Aggregated performance insights."""
    total_posts: int
    platforms: List[PlatformBreakdown] = []
    top_topics: List[TopicBreakdown] = []
    top_hook_types: List[HookBreakdown] = []
    best_day_of_week: Optional[str] = None
    patterns: List[PatternDetected] = []
    top_hooks: List[str] = []          # Actual hook text from best performers
    anti_hooks: List[str] = []         # Hooks that flopped
