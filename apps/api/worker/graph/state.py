"""Pipeline state definition for the 8-node content generation graph.

The state flows through all nodes. Each node reads what it needs and
returns only the keys it updates. LangGraph merges updates automatically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class TopicCandidate(TypedDict):
    """A single scored topic candidate."""
    id: str
    title: str
    audience_pain: str
    why_now: str
    novelty_angle: str
    hooks: List[str]
    suggested_structure: str
    required_proof: str
    risk_flags: List[str]
    opportunity_score: int
    score_breakdown: Dict[str, int]
    sources: List[str]


class HookCandidate(TypedDict):
    """A single scored hook candidate."""
    id: str
    hook_text: str
    hook_type: str
    score_breakdown: Dict[str, int]
    total_score: int


class ContentPack(TypedDict, total=False):
    """The full multi-platform Content Pack."""
    # YouTube
    youtube_long: Dict[str, Any]
    youtube_shorts: List[Dict[str, Any]]
    titles: List[str]
    description: str
    tags: List[str]
    pinned_comment: str
    thumbnail_brief: List[Dict[str, Any]]
    # LinkedIn
    linkedin_posts: List[Dict[str, Any]]
    # Twitter/X
    twitter_posts: List[Dict[str, Any]]
    twitter_thread: Dict[str, Any]
    # Short-form (TikTok, Reels, Shorts beyond YouTube)
    short_form_scripts: List[Dict[str, Any]]
    # Ad copy (Facebook, Instagram, LinkedIn ads)
    ad_copy: List[Dict[str, Any]]
    # Carousel slides (LinkedIn + Instagram carousels)
    carousel_slides: List[Dict[str, Any]]


class TestResult(TypedDict):
    """Test result for a single asset."""
    asset_type: str
    passed: bool
    issues: List[str]
    risk_flags: List[str]


class PipelineState(TypedDict, total=False):
    """Full state for the content generation pipeline.

    Each node reads what it needs and returns only updated keys.
    LangGraph merges partial updates into the full state.
    """
    # ── Inputs (set once at start) ──────────────────────────
    workflow_id: str
    user_id: str
    goal_text: str
    profile_snapshot: Dict[str, Any]
    settings: Dict[str, Any]

    # ── Research phase ──────────────────────────────────────
    research_signals: List[Dict[str, Any]]
    topic_candidates: List[TopicCandidate]

    # ── Selection phase ─────────────────────────────────────
    selected_topic: Optional[TopicCandidate]
    hook_candidates: List[HookCandidate]
    selected_hook: Optional[HookCandidate]

    # ── Generation phase ────────────────────────────────────
    content_pack: Optional[ContentPack]

    # ── Editor phase ────────────────────────────────────────
    edited_pack: Optional[ContentPack]

    # ── Testing phase ───────────────────────────────────────
    test_report: List[TestResult]
    tests_passed: bool

    # ── Approval phase ──────────────────────────────────────
    approval_decision: Optional[str]   # "approved" or "rejected"
    rejection_feedback: Optional[str]

    # ── Tracking ────────────────────────────────────────────
    resources_used: List[str]
    current_step: str
