"""Pipeline executor: runs the LangGraph content generation pipeline.

Handles both fresh runs and resume-from-interrupt. Saves snapshots
and content assets to Supabase after each step.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langgraph.types import Command

from supabase import Client

from worker.graph.pipeline import build_graph, create_initial_state, get_checkpointer
from worker.lifecycle import create_snapshot, update_status

logger = logging.getLogger("worker.executor")

# Map interrupt node names to workflow statuses
INTERRUPT_STATUS = {
    "topic_selection": "awaiting_topic",
    "hook_lab": "awaiting_hook",
    "approval": "awaiting_approval",
}

# Pipeline steps in order (for reference)
PIPELINE_STEPS = [
    "signal_research",
    "gap_analysis_topic_candidates",
    "topic_selection",
    "hook_lab",
    "script_generation",
    "editor",
    "testing",
    "approval",
]


def _save_content_assets(
    client: Client,
    workflow_id: str,
    state: Dict[str, Any],
) -> None:
    """Save generated content assets to the content_assets table."""
    # Save topic candidates
    if state.get("topic_candidates"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "topic_candidates",
            "content_json": {"candidates": state["topic_candidates"]},
            "version": 1,
        }).execute()

    # Save hook candidates
    if state.get("hook_candidates"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "hook_candidates",
            "content_json": {"candidates": state["hook_candidates"]},
            "version": 1,
        }).execute()

    # Save content pack assets
    pack = state.get("edited_pack") or state.get("content_pack")
    if pack:
        _save_pack_assets(client, workflow_id, pack)


def _save_pack_assets(
    client: Client,
    workflow_id: str,
    pack: Dict[str, Any],
) -> None:
    """Save individual content pack assets."""
    if pack.get("youtube_long"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "youtube_long",
            "content_json": pack["youtube_long"],
            "version": 1,
        }).execute()

    for i, short in enumerate(pack.get("youtube_shorts", [])):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "youtube_short",
            "content_json": {**short, "short_index": i + 1},
            "version": 1,
        }).execute()

    if pack.get("titles"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "title_set",
            "content_json": {"titles": pack["titles"]},
            "version": 1,
        }).execute()

    if pack.get("description"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "description",
            "content_json": {"description": pack["description"]},
            "version": 1,
        }).execute()

    if pack.get("tags"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "tags",
            "content_json": {"tags": pack["tags"]},
            "version": 1,
        }).execute()

    if pack.get("pinned_comment"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "pinned_comment",
            "content_json": {"pinned_comment": pack["pinned_comment"]},
            "version": 1,
        }).execute()

    if pack.get("thumbnail_brief"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "thumbnail_brief",
            "content_json": {"concepts": pack["thumbnail_brief"]},
            "version": 1,
        }).execute()


def _save_test_report(
    client: Client,
    workflow_id: str,
    state: Dict[str, Any],
) -> None:
    """Save test report as a content asset."""
    if state.get("test_report"):
        client.table("content_assets").insert({
            "workflow_id": workflow_id,
            "type": "test_report",
            "content_json": {
                "results": state["test_report"],
                "overall_passed": state.get("tests_passed", False),
            },
            "version": 1,
        }).execute()


def run_pipeline(
    client: Client,
    workflow_id: str,
    action: str = "run",
    resume_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """Run the LangGraph pipeline. Returns the final workflow status.

    Args:
        client: Supabase admin client
        workflow_id: The workflow to process
        action: "run" for fresh start, "resume" for interrupt continuation
        resume_payload: User's selection data for resume
    """
    config = {"configurable": {"thread_id": workflow_id}}
    checkpointer = get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)

    if action == "run":
        # Fresh run: load workflow data and create initial state
        resp = (
            client.table("workflows")
            .select("user_id, goal_text, settings, profile_snapshot")
            .eq("id", workflow_id)
            .execute()
        )
        if not resp.data:
            raise ValueError(f"Workflow {workflow_id} not found")

        wf = resp.data[0]
        initial_state = create_initial_state(
            workflow_id=workflow_id,
            user_id=wf["user_id"],
            goal_text=wf["goal_text"],
            profile_snapshot=wf.get("profile_snapshot", {}),
            workflow_settings=wf.get("settings", {}),
        )

        logger.info("Starting pipeline for workflow %s", workflow_id)
        result = graph.invoke(initial_state, config=config)

    elif action == "resume":
        if not resume_payload:
            raise ValueError("resume_payload required for action=resume")

        # Transition from awaiting_* back to running
        resp = (
            client.table("workflows")
            .select("status")
            .eq("id", workflow_id)
            .execute()
        )
        if resp.data and resp.data[0]["status"].startswith("awaiting_"):
            update_status(client, workflow_id, "running")

        logger.info(
            "Resuming pipeline for workflow %s with keys=%s",
            workflow_id, list(resume_payload.keys()),
        )
        result = graph.invoke(Command(resume=resume_payload), config=config)
    else:
        raise ValueError(f"Unknown action: {action}")

    # Determine outcome: did we hit an interrupt or complete?
    final_state = result if isinstance(result, dict) else {}

    # Check for pending interrupts
    graph_state = graph.get_state(config)
    has_interrupt = False
    interrupt_node = ""

    for task in getattr(graph_state, "tasks", []):
        if hasattr(task, "interrupts") and task.interrupts:
            has_interrupt = True
            interrupt_node = getattr(task, "name", "")
            break

    if has_interrupt and interrupt_node in INTERRUPT_STATUS:
        interrupt_status = INTERRUPT_STATUS[interrupt_node]

        # Save snapshot
        create_snapshot(client, workflow_id, interrupt_node, state_json={
            "step": interrupt_node,
            "status": "interrupted",
        })

        # Save any assets generated so far
        _save_content_assets(client, workflow_id, final_state)

        # Update workflow status
        update_status(
            client, workflow_id, interrupt_status,
            current_step=interrupt_node,
        )

        logger.info(
            "Pipeline interrupted at %s (status=%s) for workflow %s",
            interrupt_node, interrupt_status, workflow_id,
        )
        return interrupt_status

    # Pipeline completed
    create_snapshot(client, workflow_id, "approval", state_json={
        "step": "approval",
        "status": "completed",
        "decision": final_state.get("approval_decision", "approved"),
    })

    _save_content_assets(client, workflow_id, final_state)
    _save_test_report(client, workflow_id, final_state)

    final_decision = final_state.get("approval_decision", "approved")
    final_status = "approved" if final_decision == "approved" else "rejected"

    update_status(client, workflow_id, final_status, current_step="approval")

    logger.info(
        "Pipeline completed for workflow %s (decision=%s)",
        workflow_id, final_decision,
    )
    return final_status
