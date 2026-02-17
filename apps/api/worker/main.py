"""Worker entry point: polls for queued workflows and processes them.

Handles both fresh runs (status=queued) and resume-from-interrupt
(status=queued + settings._resume present).

Usage:
    cd apps/api
    python3 -m worker.main
"""

import app.openai_compat_patch  # noqa: F401  -- must be first to patch before any OpenAI usage

import logging
import signal
import time
from pathlib import Path

# Ensure project root .env is loaded before any config imports
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

from supabase import create_client  # noqa: E402

from app.config import settings  # noqa: E402
from worker.executor import run_pipeline  # noqa: E402
from worker.lifecycle import mark_failed  # noqa: E402
from worker.queue import claim_next_job, release_claim  # noqa: E402

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

# ── Globals ──────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 2

_running = True


def _shutdown(signum, _frame):
    """Signal handler for graceful shutdown."""
    global _running
    sig_name = signal.Signals(signum).name
    logger.info("Received %s — finishing current job then stopping...", sig_name)
    _running = False


def _get_admin_client():
    """Create a Supabase client with service-role key (bypasses RLS)."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def process_job(client, workflow: dict) -> None:
    """Process a claimed workflow — either fresh run or resume."""
    workflow_id = workflow["id"]
    wf_settings = workflow.get("settings", {}) or {}
    resume_payload = wf_settings.get("_resume")
    current_step = workflow.get("current_step")

    if resume_payload and current_step:
        # Resume from interrupt
        logger.info(
            "Resuming workflow %s from step %s",
            workflow_id, current_step,
        )
        run_pipeline(
            client=client,
            workflow_id=workflow_id,
            action="resume",
            resume_payload=resume_payload,
        )

        # Clear the resume data from settings
        clean_settings = {k: v for k, v in wf_settings.items() if k != "_resume"}
        client.table("workflows").update(
            {"settings": clean_settings}
        ).eq("id", workflow_id).execute()
    else:
        # Fresh run
        logger.info("Processing workflow %s (fresh run)", workflow_id)
        run_pipeline(
            client=client,
            workflow_id=workflow_id,
            action="run",
        )


def main():
    """Main worker loop: poll → claim → process → repeat."""
    global _running

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    client = _get_admin_client()
    logger.info(
        "Worker started. Polling for queued workflows every %ds...",
        POLL_INTERVAL_SECONDS,
    )

    while _running:
        try:
            workflow = claim_next_job(client)
        except Exception:
            logger.exception("Error during claim, sleeping before retry")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if workflow is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        workflow_id = workflow["id"]

        try:
            process_job(client, workflow)
            # Clear the claimed_at timestamp on success
            release_claim(client, workflow_id)
            logger.info("Job completed: workflow=%s", workflow_id)
        except Exception as e:
            logger.exception("Job failed: workflow=%s", workflow_id)
            retry_count = workflow.get("retry_count", 0)
            try:
                # Increment retry count and mark failed
                client.table("workflows").update({
                    "retry_count": retry_count + 1,
                    "claimed_at": None,
                }).eq("id", workflow_id).execute()
                mark_failed(client, workflow_id, str(e))
            except Exception:
                logger.exception("Error marking workflow %s as failed", workflow_id)

    logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
