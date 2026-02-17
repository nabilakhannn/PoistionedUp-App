"""Node 8: Approval — interrupt and wait for user to approve or reject."""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.types import interrupt

logger = logging.getLogger("worker.graph.nodes.approval")


def approval(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pause the pipeline for user approval.

    Sends the edited content pack + test report to the user.
    User can approve, reject with feedback, or request regeneration.
    """
    edited_pack = state.get("edited_pack", state.get("content_pack", {}))
    test_report = state.get("test_report", [])
    tests_passed = state.get("tests_passed", True)

    logger.info(
        "approval: interrupting for user decision (tests_passed=%s)",
        tests_passed,
    )

    user_decision = interrupt({
        "type": "approval",
        "content_pack": edited_pack,
        "test_report": test_report,
        "tests_passed": tests_passed,
    })

    decision = user_decision.get("decision", "approved")
    feedback = user_decision.get("feedback", "")

    logger.info(
        "approval: user decision=%s feedback=%s",
        decision, feedback[:100] if feedback else "none",
    )

    return {
        "approval_decision": decision,
        "rejection_feedback": feedback if decision == "rejected" else None,
        "current_step": "approval",
    }
