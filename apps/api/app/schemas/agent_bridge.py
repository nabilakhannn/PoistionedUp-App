"""Schemas for the Agent Bridge API.

These schemas define the data contracts between OpenClaw agents
and the PositionedUp brain. Agents call these endpoints to:
- Pull brand context (profile, memory, performance, voice)
- Search knowledge base semantically
- Report findings and observations
- Trigger the content pipeline
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Context endpoint ──────────────────────────────────────

class BrandContext(BaseModel):
    """Full brand context for an agent, aggregated in one call."""
    brand_id: str
    brand_name: str
    completeness_pct: float = 0.0
    profile: Dict[str, Any] = Field(default_factory=dict)
    recent_memories: List[Dict[str, Any]] = Field(default_factory=list)
    performance_summary: Dict[str, Any] = Field(default_factory=dict)
    voice_dna: Dict[str, Any] = Field(default_factory=dict)
    active_experiments: List[Dict[str, Any]] = Field(default_factory=list)
    content_pillars: List[str] = Field(default_factory=list)
    writing_rules: str = ""


# ── Knowledge search ──────────────────────────────────────

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    brand_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)
    threshold: float = Field(0.65, ge=0.0, le=1.0)
    gold_only: bool = False


class KnowledgeChunk(BaseModel):
    resource_id: str
    resource_title: str
    section: Optional[str] = None
    is_gold: bool = False
    chunk_text: str
    similarity: float
    tags: List[str] = Field(default_factory=list)


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: List[KnowledgeChunk] = Field(default_factory=list)
    total_found: int = 0


# ── Agent report / observation ────────────────────────────

class AgentReport(BaseModel):
    agent_id: str = Field(..., description="ID of the agent filing the report")
    task_id: Optional[str] = Field(None, description="Related task ID if any")
    brand_id: Optional[str] = None
    report_type: str = Field(
        "observation",
        description="Type: observation, finding, insight, deliverable, status_update"
    )
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1, max_length=50000)
    tags: List[str] = Field(default_factory=list)
    save_to_memory: bool = Field(True, description="Also save as agent memory entry")


class AgentReportResponse(BaseModel):
    message_id: Optional[str] = None
    memory_id: Optional[str] = None
    deliverable_id: Optional[str] = None


# ── Pipeline trigger ──────────────────────────────────────

class PipelineTriggerRequest(BaseModel):
    brand_id: str
    topic: Optional[str] = Field(None, description="Pre-selected topic (skips research)")
    objective: str = Field("personal_branding", description="Content objective")
    content_type: str = Field("educational", description="Content type")
    platforms: List[str] = Field(default_factory=lambda: ["youtube_long"])
    tone: str = "conversational"
    content_length: str = "medium"


class PipelineTriggerResponse(BaseModel):
    workflow_id: str
    status: str


# ── Task sync ─────────────────────────────────────────────

class TaskBoardEntry(BaseModel):
    """Single task from task_board.md, synced by an agent."""
    id: str
    title: str
    brief: Optional[str] = None
    priority: str = "P2"
    status: str = "backlog"
    assignee_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    notes: Optional[str] = None


class TaskSyncRequest(BaseModel):
    """Batch of tasks to upsert from an agent."""
    agent_id: str
    tasks: List[TaskBoardEntry] = Field(default_factory=list)


class TaskSyncResponse(BaseModel):
    created: int = 0
    updated: int = 0
    total: int = 0


# ── Inspo items ───────────────────────────────────────────

class InspoSearchRequest(BaseModel):
    board_id: Optional[str] = None
    brand_id: Optional[str] = None
    query: Optional[str] = Field(None, max_length=500)
    starred_only: bool = False
    limit: int = Field(20, ge=1, le=100)


# ── Heartbeat ─────────────────────────────────────────────

class AgentHeartbeat(BaseModel):
    agent_id: str
    status: str = "idle"
    status_reason: Optional[str] = None
    current_task_id: Optional[str] = None


# ── Competitor intelligence (agent-facing) ────────────────

VALID_COMPETITOR_ALERT_TYPES = {
    "follower_surge", "engagement_drop", "positioning_shift",
    "content_spike", "new_strategy",
}


class CompetitorAlertSubmission(BaseModel):
    """Agent submits a structured competitor alert."""
    agent_id: str
    competitor_id: str
    alert_type: str
    detail: str = Field(..., min_length=1, max_length=5000)
    metric_before: Optional[float] = None
    metric_after: Optional[float] = None
    severity: str = Field("medium")
    brand_id: Optional[str] = None

    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in VALID_COMPETITOR_ALERT_TYPES:
            raise ValueError(
                f"Invalid alert_type: {v}. "
                f"Valid: {sorted(VALID_COMPETITOR_ALERT_TYPES)}"
            )
        return v

    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in ("low", "medium", "high"):
            raise ValueError("severity must be 'low', 'medium', or 'high'")
        return v
