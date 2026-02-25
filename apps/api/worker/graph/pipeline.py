"""Graph compilation and checkpointing for the content pipeline.

Builds the 8-node LangGraph state machine with PostgresSaver for
durable checkpoints. Interrupted graphs can resume from any point.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from worker.graph.nodes.approval import approval
from worker.graph.nodes.editor import editor
from worker.graph.nodes.gap_analysis import gap_analysis
from worker.graph.nodes.hook_lab import hook_lab
from worker.graph.nodes.script_generation import script_generation
from worker.graph.nodes.signal_research import signal_research
from worker.graph.nodes.testing import testing
from worker.graph.nodes.topic_selection import topic_selection
from worker.graph.state import PipelineState

logger = logging.getLogger("worker.graph.pipeline")

# Module-level checkpointer singleton (lazy init)
_checkpointer: Optional[Any] = None
_checkpointer_cm: Optional[Any] = None  # Keep reference to context manager


def get_checkpointer() -> Any:
    """Get or create the pipeline checkpointer.

    Tries PostgresSaver first (for durable checkpoints across restarts).
    Falls back to MemorySaver if no Postgres connection is available.

    Note: newer langgraph-checkpoint-postgres versions return a
    context manager from from_conn_string(). We enter it manually
    and keep the reference alive at module level.
    """
    global _checkpointer, _checkpointer_cm
    if _checkpointer is not None:
        return _checkpointer

    from app.config import settings

    db_uri = settings.langgraph_db_uri

    # Try PostgresSaver first
    if db_uri and db_uri.strip():
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            logger.info("Initializing PostgresSaver with %s", db_uri[:30] + "...")

            cm = PostgresSaver.from_conn_string(db_uri)

            # Newer versions return a context manager, older return the instance
            if hasattr(cm, "__enter__"):
                _checkpointer_cm = cm
                _checkpointer = cm.__enter__()
            else:
                _checkpointer = cm

            _checkpointer.setup()
            logger.info("PostgresSaver ready (checkpoint tables created)")
            return _checkpointer
        except Exception as e:
            logger.warning(
                "PostgresSaver init failed (%s), falling back to MemorySaver", e
            )

    # Fallback: in-memory checkpointer (no persistence across restarts)
    from langgraph.checkpoint.memory import MemorySaver

    logger.info("Using MemorySaver (in-memory checkpoints, no persistence)")
    _checkpointer = MemorySaver()
    return _checkpointer


def build_graph(checkpointer: Optional[Any] = None) -> Any:
    """Build and compile the 8-node content pipeline graph.

    Args:
        checkpointer: Optional PostgresSaver for durable checkpoints.
                      If None, uses in-memory state (for testing).
    """
    graph = StateGraph(PipelineState)

    # Add all 8 nodes
    graph.add_node("signal_research", signal_research)
    graph.add_node("gap_analysis", gap_analysis)
    graph.add_node("topic_selection", topic_selection)
    graph.add_node("hook_lab", hook_lab)
    graph.add_node("script_generation", script_generation)
    graph.add_node("editor", editor)
    graph.add_node("testing", testing)
    graph.add_node("approval", approval)

    # Define the sequential flow
    graph.add_edge(START, "signal_research")
    graph.add_edge("signal_research", "gap_analysis")
    graph.add_edge("gap_analysis", "topic_selection")
    graph.add_edge("topic_selection", "hook_lab")
    graph.add_edge("hook_lab", "script_generation")
    graph.add_edge("script_generation", "editor")
    graph.add_edge("editor", "testing")
    graph.add_edge("testing", "approval")
    graph.add_edge("approval", END)

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Pipeline graph compiled: 8 nodes, 3 interrupt points")
    return compiled


def create_initial_state(
    workflow_id: str,
    user_id: str,
    goal_text: str,
    profile_snapshot: Dict[str, Any],
    workflow_settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Create the initial state dict for a new pipeline run."""
    return {
        "workflow_id": workflow_id,
        "user_id": user_id,
        "goal_text": goal_text,
        "profile_snapshot": profile_snapshot,
        "settings": workflow_settings,
        "research_signals": [],
        "topic_candidates": [],
        "selected_topic": None,
        "hook_candidates": [],
        "selected_hook": None,
        "content_pack": None,
        "edited_pack": None,
        "test_report": [],
        "tests_passed": False,
        "approval_decision": None,
        "rejection_feedback": None,
        "resources_used": [],
        "current_step": "",
    }
