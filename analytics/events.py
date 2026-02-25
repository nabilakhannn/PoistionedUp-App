"""Event type registry and property schemas.

Open/Closed Principle: New event types are added by extending the
EventType class constants and creating new dataclass schemas.
No existing code needs to change when adding new event categories.

Interface Segregation: Each event category has its own property
schema (TaskProperties, HeartbeatProperties, etc.) so consumers
only depend on the properties they need.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Event Type Constants
# ---------------------------------------------------------------------------

class EventType:
    """Registry of all tracked event names.

    Naming convention: agent_{category}_{action}
    This ensures clean filtering in PostHog dashboards.

    To add a new event:
    1. Add the constant here
    2. Create a property schema dataclass if needed
    3. Add a tracking method to AgentTracker
    """

    # --- Task Lifecycle ---
    TASK_CREATED = "agent_task_created"
    TASK_CLAIMED = "agent_task_claimed"
    TASK_PROGRESSED = "agent_task_progressed"
    TASK_COMPLETED = "agent_task_completed"
    TASK_FAILED = "agent_task_failed"
    TASK_BLOCKED = "agent_task_blocked"
    TASK_APPROVED = "agent_task_approved"
    TASK_REJECTED = "agent_task_rejected"
    TASK_PUBLISHED = "agent_task_published"
    TASK_ARCHIVED = "agent_task_archived"

    # --- Heartbeat ---
    HEARTBEAT_PULSE = "agent_heartbeat_pulse"
    HEARTBEAT_ACTION = "agent_heartbeat_action"
    HEARTBEAT_IDLE = "agent_heartbeat_idle"
    HEARTBEAT_ERROR = "agent_heartbeat_error"

    # --- Agent Lifecycle ---
    AGENT_SPAWNED = "agent_spawned"
    AGENT_READY = "agent_ready"
    AGENT_TERMINATED = "agent_terminated"

    # --- Content ---
    CONTENT_DRAFTED = "agent_content_drafted"
    CONTENT_REVISED = "agent_content_revised"
    CONTENT_POSTED = "agent_content_posted"
    CONTENT_PERFORMANCE = "agent_content_performance"

    # --- Research ---
    RESEARCH_STARTED = "agent_research_started"
    RESEARCH_COMPLETED = "agent_research_completed"
    RESEARCH_QUERY = "agent_research_query"

    # --- Cost ---
    COST_LLM_CALL = "agent_llm_call"
    COST_DAILY_TOTAL = "agent_daily_cost"
    COST_BUDGET_WARNING = "agent_budget_warning"
    COST_BUDGET_EXCEEDED = "agent_budget_exceeded"

    # --- Communication ---
    SQUAD_MESSAGE = "agent_squad_message"
    HUMAN_MESSAGE = "agent_human_message"
    ESCALATION = "agent_escalation"

    # --- System ---
    SYSTEM_STARTUP = "agent_system_startup"
    SYSTEM_SHUTDOWN = "agent_system_shutdown"
    SYSTEM_ERROR = "agent_system_error"
    SYSTEM_CONFIG_CHANGE = "agent_system_config_change"

    @classmethod
    def all_events(cls) -> List[str]:
        """Return all registered event type strings."""
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, str) and not k.startswith("_")
        ]

    @classmethod
    def task_events(cls) -> List[str]:
        """Return only task lifecycle events."""
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, str) and k.startswith("TASK_")
        ]

    @classmethod
    def cost_events(cls) -> List[str]:
        """Return only cost tracking events."""
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, str) and k.startswith("COST_")
        ]


# ---------------------------------------------------------------------------
# Property Schemas (dataclasses with to_dict serialization)
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    """Generate UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BaseProperties:
    """Properties included in every event.

    All event property schemas inherit from this base.
    Provides consistent agent identification and timestamping.
    """

    agent_id: str
    timestamp: str = field(default_factory=_utcnow_iso)
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to PostHog-compatible dict, dropping None values."""
        result = {}
        for k, v in asdict(self).items():
            if v is None:
                continue
            if isinstance(v, list):
                result[k] = ",".join(str(item) for item in v) if v else ""
            else:
                result[k] = v
        return result


@dataclass
class TaskProperties(BaseProperties):
    """Properties for task lifecycle events.

    Captures the full context of a task state change.
    """

    task_id: str = ""
    task_title: str = ""
    priority: str = ""
    content_type: str = ""
    platform: str = ""
    tags: List[str] = field(default_factory=list)
    assignee: str = ""
    upstream_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    deliverable_path: Optional[str] = None
    feedback: Optional[str] = None


@dataclass
class HeartbeatProperties(BaseProperties):
    """Properties for heartbeat pulse events.

    Captures system state at each heartbeat check-in.
    """

    rule_triggered: Optional[str] = None
    tasks_in_backlog: int = 0
    tasks_in_progress: int = 0
    tasks_in_review: int = 0
    tasks_ready: int = 0
    tasks_archived: int = 0
    pulse_duration_ms: Optional[int] = None
    actions_taken: int = 0


@dataclass
class CostProperties(BaseProperties):
    """Properties for LLM cost tracking events.

    Tracks token usage and cost at per-call and per-day granularity.
    """

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    daily_total_usd: float = 0.0
    budget_limit_usd: float = 0.0
    budget_percent_used: float = 0.0
    step_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Auto-calculate total tokens if not provided."""
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class ContentProperties(BaseProperties):
    """Properties for content creation events."""

    content_type: str = ""
    platform: str = ""
    word_count: int = 0
    slide_count: int = 0
    revision_number: int = 0
    file_path: str = ""
    post_url: Optional[str] = None
    engagement_rate: Optional[float] = None
    performance_tier: Optional[str] = None


@dataclass
class ResearchProperties(BaseProperties):
    """Properties for research activity events."""

    source: str = ""
    query: str = ""
    results_count: int = 0
    top_score: float = 0.0
    findings_file: Optional[str] = None
    duration_seconds: Optional[int] = None


@dataclass
class AgentProperties(BaseProperties):
    """Properties for agent lifecycle events."""

    role: str = ""
    parent_agent: str = ""
    model: str = ""
    tools: List[str] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass
class CommunicationProperties(BaseProperties):
    """Properties for inter-agent communication events."""

    target_agent: str = ""
    message_type: str = ""
    channel: str = ""
    message_length: int = 0


@dataclass
class SystemProperties(BaseProperties):
    """Properties for system-level events."""

    component: str = ""
    error_message: Optional[str] = None
    config_key: Optional[str] = None
    config_value: Optional[str] = None
    version: str = ""
