"""Main tracking facade - the primary interface for all agent analytics.

Facade Pattern: Provides a single, clean interface that hides the
complexity of PostHog client management, event schemas, and property
serialization from consumers.

Interface Segregation: Methods are grouped by domain (tasks, heartbeat,
cost, content, research, agents, system). Consumers only interact with
the methods they need.

Dependency Inversion: Depends on PostHogClient abstraction, not the
PostHog SDK directly. This makes testing trivial (inject a mock client).

Usage:
    tracker = AgentTracker.create()
    tracker.task_created(agent_id="jumbo", task_id="PU-001", title="Research trends")
    tracker.heartbeat_pulse(agent_id="jumbo", backlog=3)
    tracker.llm_call(agent_id="copywriter", model="opus", input_tokens=500, ...)
    tracker.flush()
"""

import logging
from typing import Any, Dict, List, Optional

from analytics.client import PostHogClient, get_client
from analytics.config import AnalyticsConfig
from analytics.events import (
    EventType,
    TaskProperties,
    HeartbeatProperties,
    CostProperties,
    ContentProperties,
    ResearchProperties,
    AgentProperties,
    CommunicationProperties,
    SystemProperties,
)

logger = logging.getLogger(__name__)


class AgentTracker:
    """Facade for tracking all OpenClaw agent analytics events.

    This is the ONLY class consumers should interact with. It handles
    event construction, property serialization, and PostHog delivery.

    Example:
        tracker = AgentTracker.create()
        tracker.task_created("jumbo", "PU-001", "Weekly trend research")
        tracker.heartbeat_pulse("jumbo", backlog=3, in_progress=1)
        tracker.llm_call("copywriter", "claude-opus", 1200, 800, 0.04)
        tracker.flush()
    """

    def __init__(
        self,
        client: PostHogClient,
        system_id: str = "positionedup-squad",
    ) -> None:
        """Initialize tracker with an existing PostHog client.

        Args:
            client: PostHog client instance.
            system_id: Unique identifier for this agent system.
        """
        self._client = client
        self._system_id = system_id

    @classmethod
    def create(
        cls,
        config: Optional[AnalyticsConfig] = None,
        system_id: str = "positionedup-squad",
    ) -> "AgentTracker":
        """Factory method to create a tracker with auto-configured client.

        Args:
            config: Optional configuration override.
            system_id: System identifier.

        Returns:
            Configured AgentTracker instance.
        """
        client = get_client(config)
        return cls(client, system_id)

    # ------------------------------------------------------------------
    # Task Lifecycle
    # ------------------------------------------------------------------

    def task_created(
        self,
        agent_id: str,
        task_id: str,
        title: str,
        priority: str = "P2",
        content_type: str = "",
        platform: str = "",
        tags: Optional[List[str]] = None,
        assignee: str = "",
        upstream_id: Optional[str] = None,
    ) -> None:
        """Track a new task being added to the backlog."""
        props = TaskProperties(
            agent_id=agent_id,
            task_id=task_id,
            task_title=title,
            priority=priority,
            content_type=content_type,
            platform=platform,
            tags=tags or [],
            assignee=assignee,
            upstream_id=upstream_id,
        )
        self._emit(agent_id, EventType.TASK_CREATED, props.to_dict())

    def task_claimed(
        self,
        agent_id: str,
        task_id: str,
        title: str = "",
    ) -> None:
        """Track an agent claiming a task from the backlog."""
        props = TaskProperties(
            agent_id=agent_id,
            task_id=task_id,
            task_title=title,
            assignee=agent_id,
        )
        self._emit(agent_id, EventType.TASK_CLAIMED, props.to_dict())

    def task_progressed(
        self,
        agent_id: str,
        task_id: str,
        status: str,
    ) -> None:
        """Track a task status update (e.g., 'research done, writing started')."""
        props = TaskProperties(agent_id=agent_id, task_id=task_id)
        extra = props.to_dict()
        extra["new_status"] = status
        self._emit(agent_id, EventType.TASK_PROGRESSED, extra)

    def task_completed(
        self,
        agent_id: str,
        task_id: str,
        title: str = "",
        duration_seconds: Optional[int] = None,
        deliverable_path: Optional[str] = None,
    ) -> None:
        """Track a task being completed with deliverables."""
        props = TaskProperties(
            agent_id=agent_id,
            task_id=task_id,
            task_title=title,
            duration_seconds=duration_seconds,
            deliverable_path=deliverable_path,
        )
        self._emit(agent_id, EventType.TASK_COMPLETED, props.to_dict())

    def task_failed(
        self,
        agent_id: str,
        task_id: str,
        reason: str = "",
    ) -> None:
        """Track a task failure."""
        props = TaskProperties(agent_id=agent_id, task_id=task_id)
        extra = props.to_dict()
        extra["failure_reason"] = reason
        self._emit(agent_id, EventType.TASK_FAILED, extra)

    def task_blocked(
        self,
        agent_id: str,
        task_id: str,
        reason: str = "",
    ) -> None:
        """Track a task being blocked (waiting on dependency or human)."""
        props = TaskProperties(agent_id=agent_id, task_id=task_id)
        extra = props.to_dict()
        extra["blocked_reason"] = reason
        self._emit(agent_id, EventType.TASK_BLOCKED, extra)

    def task_approved(
        self,
        task_id: str,
        approver: str = "human",
    ) -> None:
        """Track human approval of a task deliverable."""
        props = TaskProperties(agent_id=approver, task_id=task_id)
        self._emit(approver, EventType.TASK_APPROVED, props.to_dict())

    def task_rejected(
        self,
        task_id: str,
        feedback: str = "",
        rejector: str = "human",
    ) -> None:
        """Track human rejection of a task deliverable."""
        props = TaskProperties(
            agent_id=rejector,
            task_id=task_id,
            feedback=feedback,
        )
        self._emit(rejector, EventType.TASK_REJECTED, props.to_dict())

    def task_published(
        self,
        agent_id: str,
        task_id: str,
        platform: str,
        post_url: str = "",
    ) -> None:
        """Track content being published to a platform."""
        props = TaskProperties(
            agent_id=agent_id,
            task_id=task_id,
            platform=platform,
        )
        extra = props.to_dict()
        extra["post_url"] = post_url
        self._emit(agent_id, EventType.TASK_PUBLISHED, extra)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat_pulse(
        self,
        agent_id: str,
        backlog: int = 0,
        in_progress: int = 0,
        review: int = 0,
        ready: int = 0,
        archived: int = 0,
        rule_triggered: Optional[str] = None,
        actions_taken: int = 0,
        pulse_duration_ms: Optional[int] = None,
    ) -> None:
        """Track a 15-minute heartbeat check-in.

        Emits HEARTBEAT_ACTION if the agent did something,
        HEARTBEAT_IDLE if nothing needed attention.
        """
        event = (
            EventType.HEARTBEAT_ACTION
            if rule_triggered or actions_taken > 0
            else EventType.HEARTBEAT_IDLE
        )
        props = HeartbeatProperties(
            agent_id=agent_id,
            rule_triggered=rule_triggered,
            tasks_in_backlog=backlog,
            tasks_in_progress=in_progress,
            tasks_in_review=review,
            tasks_ready=ready,
            tasks_archived=archived,
            pulse_duration_ms=pulse_duration_ms,
            actions_taken=actions_taken,
        )
        self._emit(agent_id, event, props.to_dict())

    def heartbeat_error(
        self,
        agent_id: str,
        error: str,
    ) -> None:
        """Track a heartbeat failure."""
        props = HeartbeatProperties(agent_id=agent_id)
        extra = props.to_dict()
        extra["error_message"] = error
        self._emit(agent_id, EventType.HEARTBEAT_ERROR, extra)

    # ------------------------------------------------------------------
    # Cost Tracking
    # ------------------------------------------------------------------

    def llm_call(
        self,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        step_name: Optional[str] = None,
    ) -> None:
        """Track a single LLM API call with token counts and cost."""
        props = CostProperties(
            agent_id=agent_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost_usd,
            step_name=step_name,
        )
        self._emit(agent_id, EventType.COST_LLM_CALL, props.to_dict())

    def daily_cost(
        self,
        total_usd: float,
        budget_limit_usd: float = 0.0,
    ) -> None:
        """Track daily cost summary."""
        budget_pct = (
            (total_usd / budget_limit_usd * 100)
            if budget_limit_usd > 0
            else 0.0
        )
        props = CostProperties(
            agent_id="system",
            daily_total_usd=total_usd,
            budget_limit_usd=budget_limit_usd,
            budget_percent_used=round(budget_pct, 1),
        )
        self._emit("system", EventType.COST_DAILY_TOTAL, props.to_dict())

    def budget_warning(
        self,
        percent_used: float,
        threshold: str = "80%",
    ) -> None:
        """Track budget threshold breach."""
        props = CostProperties(
            agent_id="system",
            budget_percent_used=percent_used,
        )
        extra = props.to_dict()
        extra["threshold"] = threshold
        self._emit("system", EventType.COST_BUDGET_WARNING, extra)

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def content_drafted(
        self,
        agent_id: str,
        content_type: str,
        platform: str,
        word_count: int = 0,
        slide_count: int = 0,
        file_path: str = "",
    ) -> None:
        """Track content draft creation."""
        props = ContentProperties(
            agent_id=agent_id,
            content_type=content_type,
            platform=platform,
            word_count=word_count,
            slide_count=slide_count,
            file_path=file_path,
        )
        self._emit(agent_id, EventType.CONTENT_DRAFTED, props.to_dict())

    def content_revised(
        self,
        agent_id: str,
        content_type: str,
        revision_number: int,
        file_path: str = "",
    ) -> None:
        """Track content revision."""
        props = ContentProperties(
            agent_id=agent_id,
            content_type=content_type,
            revision_number=revision_number,
            file_path=file_path,
        )
        self._emit(agent_id, EventType.CONTENT_REVISED, props.to_dict())

    def content_posted(
        self,
        agent_id: str,
        platform: str,
        post_url: str = "",
    ) -> None:
        """Track content being posted to a platform."""
        props = ContentProperties(
            agent_id=agent_id,
            platform=platform,
            post_url=post_url,
        )
        self._emit(agent_id, EventType.CONTENT_POSTED, props.to_dict())

    def content_performance(
        self,
        agent_id: str,
        platform: str,
        engagement_rate: float,
        performance_tier: str,
        post_url: str = "",
    ) -> None:
        """Track content performance metrics."""
        props = ContentProperties(
            agent_id=agent_id,
            platform=platform,
            engagement_rate=engagement_rate,
            performance_tier=performance_tier,
            post_url=post_url,
        )
        self._emit(agent_id, EventType.CONTENT_PERFORMANCE, props.to_dict())

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    def research_started(
        self,
        agent_id: str,
        source: str,
        query: str = "",
    ) -> None:
        """Track research activity starting."""
        props = ResearchProperties(
            agent_id=agent_id,
            source=source,
            query=query,
        )
        self._emit(agent_id, EventType.RESEARCH_STARTED, props.to_dict())

    def research_completed(
        self,
        agent_id: str,
        source: str,
        results_count: int = 0,
        top_score: float = 0.0,
        findings_file: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> None:
        """Track research activity completion."""
        props = ResearchProperties(
            agent_id=agent_id,
            source=source,
            results_count=results_count,
            top_score=top_score,
            findings_file=findings_file,
            duration_seconds=duration_seconds,
        )
        self._emit(agent_id, EventType.RESEARCH_COMPLETED, props.to_dict())

    # ------------------------------------------------------------------
    # Agent Lifecycle
    # ------------------------------------------------------------------

    def agent_spawned(
        self,
        agent_id: str,
        role: str,
        parent_agent: str = "jumbo",
        model: str = "",
        tools: Optional[List[str]] = None,
    ) -> None:
        """Track a new agent being spawned."""
        props = AgentProperties(
            agent_id=agent_id,
            role=role,
            parent_agent=parent_agent,
            model=model,
            tools=tools or [],
        )
        self._emit(agent_id, EventType.AGENT_SPAWNED, props.to_dict())

    def agent_terminated(
        self,
        agent_id: str,
        reason: str = "",
    ) -> None:
        """Track an agent being terminated."""
        props = AgentProperties(
            agent_id=agent_id,
            reason=reason,
        )
        self._emit(agent_id, EventType.AGENT_TERMINATED, props.to_dict())

    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------

    def squad_message(
        self,
        agent_id: str,
        target_agent: str,
        message_type: str = "insight",
        channel: str = "squad_chat",
        message_length: int = 0,
    ) -> None:
        """Track inter-agent communication."""
        props = CommunicationProperties(
            agent_id=agent_id,
            target_agent=target_agent,
            message_type=message_type,
            channel=channel,
            message_length=message_length,
        )
        self._emit(agent_id, EventType.SQUAD_MESSAGE, props.to_dict())

    def escalation(
        self,
        agent_id: str,
        reason: str,
        target_agent: str = "jumbo",
    ) -> None:
        """Track an escalation to orchestrator or human."""
        props = CommunicationProperties(
            agent_id=agent_id,
            target_agent=target_agent,
            message_type="escalation",
        )
        extra = props.to_dict()
        extra["escalation_reason"] = reason
        self._emit(agent_id, EventType.ESCALATION, extra)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def system_startup(self, version: str = "") -> None:
        """Track system startup."""
        props = SystemProperties(
            agent_id="system",
            component="gateway",
            version=version,
        )
        self._emit("system", EventType.SYSTEM_STARTUP, props.to_dict())

    def system_shutdown(self) -> None:
        """Track system shutdown and flush remaining events."""
        props = SystemProperties(
            agent_id="system",
            component="gateway",
        )
        self._emit("system", EventType.SYSTEM_SHUTDOWN, props.to_dict())
        self._client.flush()

    def system_error(
        self,
        error: str,
        component: str = "",
    ) -> None:
        """Track a system-level error."""
        props = SystemProperties(
            agent_id="system",
            component=component,
            error_message=error,
        )
        self._emit("system", EventType.SYSTEM_ERROR, props.to_dict())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(
        self,
        distinct_id: str,
        event: str,
        properties: Dict[str, Any],
    ) -> None:
        """Internal: enrich and send event to PostHog."""
        properties["system_id"] = self._system_id
        self._client.capture(distinct_id, event, properties)

    def flush(self) -> None:
        """Force-flush the event queue."""
        self._client.flush()

    @property
    def is_enabled(self) -> bool:
        """Whether analytics tracking is active."""
        return self._client.is_enabled
