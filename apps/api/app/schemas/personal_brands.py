"""Pydantic models for the personal_brands CRUD endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PersonalBrandCreate(BaseModel):
    """POST /brands — create a new personal brand."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    model_tier: Optional[str] = Field(None, description="LLM tier: budget, standard, or premium")


class PersonalBrandUpdate(BaseModel):
    """PATCH /brands/{brand_id} — update a brand."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    model_tier: Optional[str] = Field(None, description="LLM tier: budget, standard, or premium")


class PersonalBrandSummary(BaseModel):
    """Lightweight brand card for list views."""
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    model_tier: str = "budget"
    completeness: Dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class PersonalBrandDetail(BaseModel):
    """Full brand detail including profile_json."""
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    model_tier: str = "budget"
    profile_json: Dict[str, Any] = Field(default_factory=dict)
    completeness: Dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ModelTierInfo(BaseModel):
    """Info about a single model tier."""
    key: str
    label: str
    description: str
    creative_model: str
    review_model: str
    provider: str
    est_cost_per_workflow: str
    est_cost_per_chat_msg: str


class ModelTierListResponse(BaseModel):
    """GET /brands/model-tiers — available model tiers."""
    tiers: List[ModelTierInfo] = Field(default_factory=list)
    current_tier: str = "budget"


class PersonalBrandListResponse(BaseModel):
    """GET /brands — list all brands for the current user."""
    brands: List[PersonalBrandSummary] = Field(default_factory=list)
    total: int = 0
