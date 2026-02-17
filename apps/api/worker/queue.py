"""Queue client: table-based polling using workflow status.

The workflow's `status = 'queued'` IS the queue. The worker polls for
queued workflows, claims one via atomic update (optimistic locking),
and processes it.

Includes:
  - Visibility timeout: re-claim workflows stuck in 'running' for >300s
  - Retry count tracking for dead-letter queue support
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import Client

logger = logging.getLogger("worker.queue")

# Workflows stuck in 'running' longer than this are eligible for re-claim
VISIBILITY_TIMEOUT_SECONDS = 300

# Max retries before sending to dead-letter status
MAX_RETRIES = 3


def claim_next_job(client: Client) -> Optional[Dict[str, Any]]:
    """Find the oldest queued workflow and atomically claim it.

    Uses optimistic locking: UPDATE ... WHERE status = 'queued'.
    If another worker already claimed it, the update returns empty
    and we move on.

    Returns the workflow row if claimed, None if queue is empty.
    """
    # Step 1: Check for stale claims (visibility timeout recovery)
    _recover_stale_claims(client)

    # Step 2: Find the oldest queued workflow
    resp = (
        client.table("workflows")
        .select("id, user_id, goal_text, settings, current_step, retry_count")
        .eq("status", "queued")
        .order("created_at")
        .limit(1)
        .execute()
    )

    if not resp.data:
        return None

    workflow = resp.data[0]
    wf_id = workflow["id"]
    retry_count = workflow.get("retry_count", 0)

    # Step 3: Check if max retries exceeded -> move to failed (DLQ)
    if retry_count >= MAX_RETRIES:
        logger.warning(
            "Workflow %s exceeded max retries (%d/%d), marking as failed (DLQ)",
            wf_id, retry_count, MAX_RETRIES,
        )
        client.table("workflows").update({
            "status": "failed",
            "error_message": f"Exceeded max retries ({MAX_RETRIES}). Moved to dead-letter queue.",
        }).eq("id", wf_id).execute()

        # Log audit event
        try:
            user_id = workflow.get("user_id", "")
            client.table("audit_events").insert({
                "user_id": user_id,
                "workflow_id": wf_id,
                "event_type": "failed",
                "payload": {
                    "reason": "max_retries_exceeded",
                    "retry_count": retry_count,
                },
            }).execute()
        except Exception:
            logger.exception("Failed to log DLQ audit event for %s", wf_id)

        return None

    # Step 4: Atomically claim it (only succeeds if still queued)
    now = datetime.now(timezone.utc).isoformat()
    claim_resp = (
        client.table("workflows")
        .update({
            "status": "running",
            "current_step": "signal_research",
            "claimed_at": now,
        })
        .eq("id", wf_id)
        .eq("status", "queued")  # Optimistic lock
        .execute()
    )

    if not claim_resp.data:
        # Another worker claimed it between our SELECT and UPDATE
        logger.debug("Workflow %s was claimed by another worker, skipping", wf_id)
        return None

    logger.info(
        "Claimed workflow %s for processing (retry=%d)",
        wf_id, retry_count,
    )
    return workflow


def _recover_stale_claims(client: Client) -> None:
    """Find workflows stuck in 'running' past the visibility timeout
    and re-queue them with an incremented retry count.

    This handles cases where the worker crashed mid-processing.
    """
    from datetime import timedelta

    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=VISIBILITY_TIMEOUT_SECONDS)
    ).isoformat()

    # Find stale running workflows
    stale_resp = (
        client.table("workflows")
        .select("id, retry_count, claimed_at, user_id")
        .eq("status", "running")
        .lt("claimed_at", cutoff)
        .limit(5)  # Process up to 5 stale claims per poll
        .execute()
    )

    if not stale_resp.data:
        return

    for row in stale_resp.data:
        wf_id = row["id"]
        old_retries = row.get("retry_count", 0)
        new_retries = old_retries + 1

        logger.warning(
            "Recovering stale workflow %s (claimed_at=%s, retry=%d->%d)",
            wf_id, row.get("claimed_at"), old_retries, new_retries,
        )

        # Re-queue with incremented retry count
        client.table("workflows").update({
            "status": "queued",
            "claimed_at": None,
            "retry_count": new_retries,
            "error_message": f"Worker timeout after {VISIBILITY_TIMEOUT_SECONDS}s (retry {new_retries})",
        }).eq("id", wf_id).eq("status", "running").execute()


def release_claim(client: Client, workflow_id: str) -> None:
    """Release a claimed workflow (clear claimed_at) after successful processing."""
    client.table("workflows").update({
        "claimed_at": None,
    }).eq("id", workflow_id).execute()
