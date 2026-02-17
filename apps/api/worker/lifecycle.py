"""Lifecycle manager: workflow status transitions and snapshot creation."""

import logging
from typing import Any, Dict, Optional

from supabase import Client

logger = logging.getLogger("worker.lifecycle")

# Valid status transitions
VALID_TRANSITIONS = {
    "queued": {"running"},
    "running": {"awaiting_topic", "awaiting_hook", "awaiting_approval", "approved", "failed"},
    "awaiting_topic": {"running", "queued"},
    "awaiting_hook": {"running", "queued"},
    "awaiting_approval": {"approved", "rejected", "queued"},
}


def update_status(
    client: Client,
    workflow_id: str,
    new_status: str,
    current_step: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Update workflow status atomically. Validates transition is allowed."""
    # Fetch current status
    resp = client.table("workflows").select("status").eq("id", workflow_id).execute()
    if not resp.data:
        raise ValueError(f"Workflow {workflow_id} not found")

    old_status = resp.data[0]["status"]
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: {old_status} -> {new_status} "
            f"(allowed: {allowed})"
        )

    update_data: Dict[str, Any] = {"status": new_status}
    if current_step is not None:
        update_data["current_step"] = current_step
    if error_message is not None:
        update_data["error_message"] = error_message

    client.table("workflows").update(update_data).eq("id", workflow_id).execute()
    logger.info(
        "Workflow %s: %s -> %s (step=%s)",
        workflow_id, old_status, new_status, current_step,
    )


def create_snapshot(
    client: Client,
    workflow_id: str,
    step_id: str,
    version: int = 1,
    state_json: Optional[Dict[str, Any]] = None,
) -> str:
    """Insert a workflow_snapshot row. Returns the snapshot ID."""
    resp = (
        client.table("workflow_snapshots")
        .insert({
            "workflow_id": workflow_id,
            "step_id": step_id,
            "version": version,
            "state_json": state_json or {},
        })
        .execute()
    )
    snapshot_id = resp.data[0]["id"]
    logger.debug("Snapshot created: workflow=%s step=%s", workflow_id, step_id)
    return snapshot_id


def mark_failed(
    client: Client,
    workflow_id: str,
    error_message: str,
    current_step: Optional[str] = None,
) -> None:
    """Set workflow to failed status with error details."""
    update_data: Dict[str, Any] = {
        "status": "failed",
        "error_message": error_message,
    }
    if current_step is not None:
        update_data["current_step"] = current_step

    client.table("workflows").update(update_data).eq("id", workflow_id).execute()

    # Log audit event
    client.table("audit_events").insert({
        "user_id": _get_workflow_user(client, workflow_id),
        "workflow_id": workflow_id,
        "event_type": "failed",
        "payload": {"error": error_message, "step": current_step},
    }).execute()

    logger.error("Workflow %s FAILED at step %s: %s", workflow_id, current_step, error_message)


def _get_workflow_user(client: Client, workflow_id: str) -> str:
    """Look up the user_id for a workflow."""
    resp = client.table("workflows").select("user_id").eq("id", workflow_id).execute()
    if not resp.data:
        raise ValueError(f"Workflow {workflow_id} not found")
    return resp.data[0]["user_id"]
