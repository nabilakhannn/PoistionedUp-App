"""Pydantic schemas for Mission Control (OpenClaw agent dashboard)."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ── Agent schemas ────────────────────────────────────────

class AgentBase(BaseModel):
    id: str
    name: str
    role: str
    role_type: str = "specialist"  # lead, specialist, integrator
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    status: str = "idle"  # idle, working, error, paused
    status_reason: Optional[str] = None
    avatar_emoji: str = "🤖"
    skills: List[str] = []
    about: Optional[str] = None
    workspace_path: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    status_reason: Optional[str] = None
    avatar_emoji: Optional[str] = None
    skills: Optional[List[str]] = None
    about: Optional[str] = None


class AgentOut(AgentBase):
    last_heartbeat_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    task_count: Optional[int] = None  # enriched in response


# ── Task schemas ─────────────────────────────────────────

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    brief: Optional[str] = Field(None, max_length=5000)
    priority: str = Field("P2", pattern="^(P0|P1|P2|P3)$")
    status: str = "backlog"
    assignee_id: Optional[str] = None
    tags: List[str] = []
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskCreate(TaskBase):
    id: str  # WOW-001 format


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    brief: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    tags: Optional[List[str]] = None
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskOut(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    assignee: Optional[AgentOut] = None  # enriched
    deliverable_count: Optional[int] = None


# ── Message schemas ──────────────────────────────────────

class MessageCreate(BaseModel):
    from_agent_id: Optional[str] = None
    to_agent_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field("chat", pattern="^(chat|delegation|status|deliverable|escalation|broadcast)$")
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageOut(BaseModel):
    id: str
    from_agent_id: Optional[str] = None
    to_agent_id: Optional[str] = None
    message: str
    message_type: str
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    from_agent: Optional[AgentOut] = None  # enriched
    to_agent: Optional[AgentOut] = None


# ── Deliverable schemas ──────────────────────────────────

class DeliverableCreate(BaseModel):
    task_id: str
    title: str = Field(..., min_length=1, max_length=500)
    file_path: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = Field(None, max_length=100000)
    deliverable_type: str = Field("document", pattern="^(document|image|code|report|content)$")
    created_by_agent_id: Optional[str] = None


class DeliverableOut(BaseModel):
    id: str
    task_id: str
    title: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    deliverable_type: str
    created_by_agent_id: Optional[str] = None
    status: str
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Dashboard stats ──────────────────────────────────────

class DashboardStats(BaseModel):
    agents_total: int
    agents_active: int
    tasks_total: int
    tasks_by_status: Dict[str, int]
    tasks_completed_today: int
    messages_today: int
    deliverables_pending_review: int


class OrchestratorActivity(BaseModel):
    delegations: List[MessageOut] = []
    recent_tasks_created: List[TaskOut] = []
    sub_agent_statuses: List[AgentOut] = []
    timeline: List[MessageOut] = []  # all message types, chronological
