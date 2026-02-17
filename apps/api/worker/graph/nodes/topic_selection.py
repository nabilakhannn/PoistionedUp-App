"""Node 3: Topic selection — interrupt and wait for user to pick a topic."""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import interrupt

logger = logging.getLogger("worker.graph.nodes.topic_selection")


def topic_selection(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pause the pipeline and wait for user to select a topic.

    Sends the topic_candidates to the caller via interrupt().
    When resumed, interrupt() returns the user's selection.
    """
    candidates = state.get("topic_candidates", [])

    logger.info(
        "topic_selection: interrupting with %d candidates",
        len(candidates),
    )

    # interrupt() pauses the graph and returns candidates to caller.
    # When the graph is resumed with Command(resume=selection),
    # interrupt() returns the selection value.
    user_selection = interrupt({
        "type": "topic_selection",
        "candidates": candidates,
    })

    # user_selection should be a dict with at least "selected_topic_id"
    selected_id = user_selection.get("selected_topic_id", "")
    selected_topic = None

    for candidate in candidates:
        if candidate.get("id") == selected_id:
            selected_topic = candidate
            break

    # If not found by ID, use the first candidate as fallback
    if selected_topic is None and candidates:
        selected_topic = candidates[0]
        logger.warning(
            "topic_selection: selected_id=%s not found, using first candidate",
            selected_id,
        )

    logger.info(
        "topic_selection: user selected topic=%s",
        selected_topic.get("title", "unknown") if selected_topic else "none",
    )

    return {
        "selected_topic": selected_topic,
        "current_step": "topic_selection",
    }
