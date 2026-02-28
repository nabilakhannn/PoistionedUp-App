"""Pydantic schemas for Agent Notifications."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: str
    title: str
    body: str
    notification_type: str
    priority: str
    from_agent_id: Optional[str] = None
    related_task_id: Optional[str] = None
    related_goal_id: Optional[str] = None
    status: str
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    read_at: Optional[datetime] = None


class UnreadCount(BaseModel):
    count: int
    by_priority: Dict[str, int] = {}


class AgentNotifyRequest(BaseModel):
    """Schema for agents to create notifications via the Bridge API."""
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=5000)
    notification_type: str = Field(
        "insight",
        pattern=r"^(briefing|reminder|alert|suggestion|insight|goal_update)$",
    )
    priority: str = Field("medium", pattern=r"^(low|medium|high|urgent)$")
    agent_id: str = Field(..., min_length=1, max_length=50)
    action_url: Optional[str] = None
    related_task_id: Optional[str] = None
