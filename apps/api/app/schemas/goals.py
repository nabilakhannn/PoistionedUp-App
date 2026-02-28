"""Pydantic schemas for the Agent Goals system."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    goal_type: str = Field(
        ...,
        pattern=r"^(posting_frequency|engagement_growth|research_cadence|content_pipeline|custom)$",
    )
    target_value: float = Field(..., gt=0)
    target_unit: str = Field("per_week", pattern=r"^(per_week|per_month|percent|count)$")
    platform: Optional[str] = None
    brand_id: Optional[str] = None
    priority: str = Field("P2", pattern=r"^(P0|P1|P2|P3)$")
    deadline_at: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = Field(None, max_length=2000)
    target_value: Optional[float] = Field(None, gt=0)
    current_value: Optional[float] = None
    status: Optional[str] = Field(None, pattern=r"^(active|paused|completed|archived)$")
    priority: Optional[str] = Field(None, pattern=r"^(P0|P1|P2|P3)$")
    deadline_at: Optional[datetime] = None


class GoalOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    goal_type: str
    target_value: float
    target_unit: str
    current_value: float
    platform: Optional[str] = None
    status: str
    priority: str
    deadline_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None
    last_action_at: Optional[datetime] = None
    brand_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
