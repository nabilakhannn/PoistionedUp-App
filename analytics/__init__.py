"""OpenClaw Agent Analytics - PostHog event tracking for multi-agent systems.

This module provides structured analytics tracking for the PositionedUp
OpenClaw agent squad. It tracks task lifecycles, agent heartbeats,
LLM costs, content creation, and research activities.

Usage:
    from analytics import AgentTracker

    tracker = AgentTracker.create()
    tracker.task_created(agent_id="jarvis", task_id="PU-001", title="Research trends")
    tracker.heartbeat_pulse(agent_id="jarvis", backlog=3, in_progress=1)
    tracker.llm_call(agent_id="copywriter", model="claude-sonnet", input_tokens=500, ...)

CLI (for agents to call via shell):
    python -m analytics track task_created --agent jarvis --task PU-001 --title "Research"
    python -m analytics track heartbeat --agent jarvis --status ok
    python -m analytics report summary

Daemon (continuous file monitoring):
    python -m analytics daemon --watch task_board.md
"""

from analytics.config import AnalyticsConfig
from analytics.client import PostHogClient, get_client
from analytics.events import EventType
from analytics.tracker import AgentTracker

__all__ = [
    "AnalyticsConfig",
    "PostHogClient",
    "get_client",
    "EventType",
    "AgentTracker",
]

__version__ = "1.0.0"
