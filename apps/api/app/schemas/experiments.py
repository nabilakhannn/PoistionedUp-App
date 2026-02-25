"""Pydantic schemas for the Experimentation + Self-Voice DNA system."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Experiments ────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    """Propose a new A/B experiment."""
    hypothesis: str = Field(..., min_length=1)
    variable: str = Field(..., min_length=1)     # hook_type, topic_category, cta_style, posting_time
    variant_a: str = Field(..., min_length=1)
    variant_b: str = Field(..., min_length=1)
    platform: str = Field(..., min_length=1)
    target_posts: int = Field(default=4, ge=2, le=20)
    brand_id: Optional[str] = None


class ExperimentUpdate(BaseModel):
    """Update experiment fields (partial)."""
    hypothesis: Optional[str] = None
    target_posts: Optional[int] = None


class ExperimentSummary(BaseModel):
    """Compact experiment listing."""
    id: str
    hypothesis: str
    variable: str
    variant_a: str
    variant_b: str
    platform: str
    status: str
    target_posts: int
    variant_a_count: int = 0
    variant_b_count: int = 0
    variant_a_avg_engagement: Optional[float] = None
    variant_b_avg_engagement: Optional[float] = None
    winner: Optional[str] = None
    conclusion: Optional[str] = None
    brand_id: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class ExperimentDetail(BaseModel):
    """Full experiment detail."""
    id: str
    hypothesis: str
    variable: str
    variant_a: str
    variant_b: str
    platform: str
    status: str
    target_posts: int
    variant_a_posts: List[str] = []
    variant_b_posts: List[str] = []
    variant_a_avg_engagement: Optional[float] = None
    variant_b_avg_engagement: Optional[float] = None
    winner: Optional[str] = None
    conclusion: Optional[str] = None
    resulting_memory_id: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class ExperimentActionResponse(BaseModel):
    """Response for approve/cancel/assign actions."""
    id: str
    status: str
    message: str


# ── Self-Voice DNA ─────────────────────────────────────────

class SelfVoiceDNA(BaseModel):
    """Voice DNA extracted from user's own published content."""
    tone: str = ""
    sentence_style: str = ""
    vocabulary_level: str = ""
    avg_sentence_length: Optional[float] = None
    hook_patterns: List[str] = []
    cta_patterns: List[str] = []
    signature_phrases: List[str] = []
    content_structure: str = ""
    personality_traits: List[str] = []
    sample_hooks: List[str] = []
    posts_analyzed: int = 0


class SelfVoiceAnalysisResponse(BaseModel):
    """Response from self-voice analysis."""
    voice_dna: SelfVoiceDNA
    message: str


class VoiceDriftResult(BaseModel):
    """Voice drift check result."""
    drift_score: float = Field(..., ge=0.0, le=1.0)  # 0 = identical, 1 = completely different
    drift_level: str       # low, medium, high
    details: List[str] = []  # Specific drift observations
    recommendation: str = ""
    baseline_available: bool = True
