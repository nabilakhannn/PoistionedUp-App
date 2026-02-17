"""Tests for worker components (Slice 4).

Verifies:
  - Queue: claim_next_job picks oldest queued workflow, optimistic lock works
  - Lifecycle: status transitions, snapshot creation, mark_failed
  - Executor: stub pipeline runs steps, interrupts at topic_selection
  - Integration: create workflow -> claim -> execute -> snapshots created
"""

import os
import uuid

import pytest
from supabase import create_client

# ── Setup ─────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

TEST_USER_EMAIL = f"test-worker-{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPassword123!"


@pytest.fixture(scope="module")
def admin():
    """Supabase admin client (service role)."""
    assert SUPABASE_URL, "SUPABASE_URL not set"
    assert SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY not set"
    return create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


@pytest.fixture(scope="module")
def test_user(admin):
    """Create a test user, yield user_id, cleanup after."""
    resp = admin.auth.admin.create_user({
        "email": TEST_USER_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = resp.user.id

    # Create profile
    admin.table("profiles").upsert({
        "user_id": user_id,
        "profile_json": {"channel_name": "WorkerTest"},
    }).execute()

    yield user_id

    # Cleanup: delete user (cascades to workflows, snapshots, etc.)
    try:
        admin.auth.admin.delete_user(user_id)
    except Exception:
        pass


def _create_test_workflow(admin, user_id: str, goal: str = "Test workflow") -> str:
    """Helper: create a workflow row and return its ID."""
    resp = (
        admin.table("workflows")
        .insert({
            "user_id": user_id,
            "status": "queued",
            "goal_text": goal,
            "settings": {},
            "profile_snapshot": {},
        })
        .execute()
    )
    return resp.data[0]["id"]


# ── Queue Tests ──────────────────────────────────────────


class TestQueue:
    """Tests for worker/queue.py (table-based polling)."""

    def test_claim_next_job_picks_oldest(self, admin, test_user):
        """claim_next_job returns the oldest queued workflow."""
        from worker.queue import claim_next_job

        # Drain any stale queued workflows from previous test runs
        while claim_next_job(admin) is not None:
            pass

        # Create two queued workflows
        wf1_id = _create_test_workflow(admin, test_user, "Queue test first")
        wf2_id = _create_test_workflow(admin, test_user, "Queue test second")

        # Claim should pick the first one
        claimed = claim_next_job(admin)
        assert claimed is not None
        assert claimed["id"] == wf1_id

        # Verify it's now running
        resp = admin.table("workflows").select("status").eq("id", wf1_id).execute()
        assert resp.data[0]["status"] == "running"

        # Second claim should pick the second one
        claimed2 = claim_next_job(admin)
        assert claimed2 is not None
        assert claimed2["id"] == wf2_id

        # Clean up
        admin.table("workflows").delete().eq("id", wf1_id).execute()
        admin.table("workflows").delete().eq("id", wf2_id).execute()

    def test_claim_empty_queue(self, admin, test_user):
        """claim_next_job returns None when no queued workflows exist."""
        from worker.queue import claim_next_job

        # Drain any leftover queued workflows
        while True:
            claimed = claim_next_job(admin)
            if claimed is None:
                break

        result = claim_next_job(admin)
        assert result is None

    def test_claim_skips_non_queued(self, admin, test_user):
        """claim_next_job only picks up status=queued, not running/failed."""
        from worker.queue import claim_next_job

        # Create workflows in non-queued states
        wf_running = _create_test_workflow(admin, test_user, "Already running")
        admin.table("workflows").update({"status": "running"}).eq("id", wf_running).execute()

        wf_failed = _create_test_workflow(admin, test_user, "Already failed")
        admin.table("workflows").update({"status": "running"}).eq("id", wf_failed).execute()
        admin.table("workflows").update({"status": "failed"}).eq("id", wf_failed).execute()

        # Drain any legitimately queued workflows
        while True:
            c = claim_next_job(admin)
            if c is None:
                break

        # Now claim should return None (running/failed are not claimable)
        result = claim_next_job(admin)
        assert result is None

        # Clean up
        admin.table("workflows").delete().eq("id", wf_running).execute()
        admin.table("workflows").delete().eq("id", wf_failed).execute()


# ── Lifecycle Tests ──────────────────────────────────────


class TestLifecycle:
    """Tests for worker/lifecycle.py functions."""

    def test_update_status_valid_transition(self, admin, test_user):
        """queued -> running is a valid transition."""
        from worker.lifecycle import update_status

        wf_id = _create_test_workflow(admin, test_user, "Lifecycle status test")
        update_status(admin, wf_id, "running", current_step="signal_research")

        # Verify
        resp = admin.table("workflows").select("status, current_step").eq("id", wf_id).execute()
        assert resp.data[0]["status"] == "running"
        assert resp.data[0]["current_step"] == "signal_research"

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()

    def test_update_status_invalid_transition(self, admin, test_user):
        """queued -> approved should be rejected."""
        from worker.lifecycle import update_status

        wf_id = _create_test_workflow(admin, test_user, "Invalid transition test")

        with pytest.raises(ValueError, match="Invalid transition"):
            update_status(admin, wf_id, "approved")

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()

    def test_running_to_awaiting_topic(self, admin, test_user):
        """running -> awaiting_topic is valid."""
        from worker.lifecycle import update_status

        wf_id = _create_test_workflow(admin, test_user, "Awaiting topic test")
        update_status(admin, wf_id, "running")
        update_status(admin, wf_id, "awaiting_topic", current_step="topic_selection")

        resp = admin.table("workflows").select("status, current_step").eq("id", wf_id).execute()
        assert resp.data[0]["status"] == "awaiting_topic"
        assert resp.data[0]["current_step"] == "topic_selection"

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()

    def test_create_snapshot(self, admin, test_user):
        """Snapshot is created with correct fields."""
        from worker.lifecycle import create_snapshot

        wf_id = _create_test_workflow(admin, test_user, "Snapshot test")
        snapshot_id = create_snapshot(admin, wf_id, "signal_research", state_json={"result": "test"})
        assert snapshot_id is not None

        # Verify
        resp = (
            admin.table("workflow_snapshots")
            .select("*")
            .eq("id", snapshot_id)
            .execute()
        )
        assert len(resp.data) == 1
        assert resp.data[0]["step_id"] == "signal_research"
        assert resp.data[0]["state_json"]["result"] == "test"

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()

    def test_mark_failed(self, admin, test_user):
        """mark_failed sets status to failed with error message and audit event."""
        from worker.lifecycle import mark_failed

        wf_id = _create_test_workflow(admin, test_user, "Mark failed test")
        # First transition to running (valid path to failed)
        admin.table("workflows").update({"status": "running"}).eq("id", wf_id).execute()

        mark_failed(admin, wf_id, "Something broke", current_step="signal_research")

        # Verify workflow status
        resp = admin.table("workflows").select("status, error_message").eq("id", wf_id).execute()
        assert resp.data[0]["status"] == "failed"
        assert resp.data[0]["error_message"] == "Something broke"

        # Verify audit event
        events = (
            admin.table("audit_events")
            .select("*")
            .eq("workflow_id", wf_id)
            .eq("event_type", "failed")
            .execute()
        )
        assert len(events.data) == 1

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()


# ── Executor Tests ───────────────────────────────────────
# NOTE: Pipeline execution tests (with mocked LLM) are in test_pipeline.py.
# The stub executor was replaced with the real LangGraph pipeline in Slice 6.


# ── Integration Tests ────────────────────────────────────


class TestWorkerIntegration:
    """End-to-end: create workflow -> claim -> execute -> verify."""

    def test_worker_handles_failure(self, admin, test_user):
        """Worker marks workflow as failed when executor raises."""
        from worker.lifecycle import mark_failed

        wf_id = _create_test_workflow(admin, test_user, "Failure handling test")
        admin.table("workflows").update({"status": "running"}).eq("id", wf_id).execute()

        # Simulate a failure
        mark_failed(admin, wf_id, "Simulated error in test", current_step="signal_research")

        # Verify
        resp = admin.table("workflows").select("status, error_message, current_step").eq("id", wf_id).execute()
        assert resp.data[0]["status"] == "failed"
        assert "Simulated error" in resp.data[0]["error_message"]
        assert resp.data[0]["current_step"] == "signal_research"

        # Clean up
        admin.table("workflows").delete().eq("id", wf_id).execute()

    def test_graceful_shutdown_flag(self):
        """SIGTERM sets _running to False for clean exit."""
        from worker import main as worker_main

        # Verify initial state
        worker_main._running = True
        assert worker_main._running is True

        # Simulate SIGTERM
        worker_main._shutdown(15, None)  # 15 = SIGTERM
        assert worker_main._running is False

        # Reset for other tests
        worker_main._running = True
