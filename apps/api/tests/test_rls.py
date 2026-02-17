"""
RLS verification tests -- Content Orchestrator Slice 2.

Proves: User A cannot see User B's data across all tables.
Uses the cloud Supabase project with real auth.

Run: cd apps/api && source .venv/bin/activate && pytest tests/test_rls.py -v
"""

import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# Test user credentials
USER_A_EMAIL = f"test-rls-a-{uuid.uuid4().hex[:8]}@test.local"
USER_B_EMAIL = f"test-rls-b-{uuid.uuid4().hex[:8]}@test.local"
TEST_PASSWORD = "TestPass123!"


def _admin_client() -> Client:
    """Service-role client (bypasses RLS)."""
    return create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


def _user_client(access_token: str) -> Client:
    """Client authenticated as a specific user (RLS enforced)."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def admin():
    return _admin_client()


@pytest.fixture(scope="module")
def user_a_session(admin):
    """Create User A and return (user_id, access_token)."""
    resp = admin.auth.admin.create_user({
        "email": USER_A_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = resp.user.id

    # Sign in to get access token
    anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    login = anon.auth.sign_in_with_password({
        "email": USER_A_EMAIL,
        "password": TEST_PASSWORD,
    })

    yield user_id, login.session.access_token

    # Cleanup: delete user (cascades all data)
    admin.auth.admin.delete_user(user_id)


@pytest.fixture(scope="module")
def user_b_session(admin):
    """Create User B and return (user_id, access_token)."""
    resp = admin.auth.admin.create_user({
        "email": USER_B_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = resp.user.id

    anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    login = anon.auth.sign_in_with_password({
        "email": USER_B_EMAIL,
        "password": TEST_PASSWORD,
    })

    yield user_id, login.session.access_token

    admin.auth.admin.delete_user(user_id)


@pytest.fixture(scope="module")
def client_a(user_a_session):
    _, token = user_a_session
    return _user_client(token)


@pytest.fixture(scope="module")
def client_b(user_b_session):
    _, token = user_b_session
    return _user_client(token)


@pytest.fixture(scope="module")
def seed_data(admin, user_a_session, user_b_session):
    """Insert test rows for both users via service-role (bypasses RLS)."""
    user_a_id, _ = user_a_session
    user_b_id, _ = user_b_session

    # Profiles (upsert because Supabase auth trigger may have created them already)
    admin.table("profiles").upsert({"user_id": user_a_id, "profile_json": {"name": "User A"}}).execute()
    admin.table("profiles").upsert({"user_id": user_b_id, "profile_json": {"name": "User B"}}).execute()

    # Resources
    res_a = admin.table("resources").insert({
        "user_id": user_a_id, "type": "note", "title": "A's note",
        "content_text": "User A content", "tags": ["test"],
    }).execute()
    res_b = admin.table("resources").insert({
        "user_id": user_b_id, "type": "note", "title": "B's note",
        "content_text": "User B content", "tags": ["test"],
    }).execute()

    resource_a_id = res_a.data[0]["id"]
    resource_b_id = res_b.data[0]["id"]

    # Resource chunks
    admin.table("resource_chunks").insert({
        "resource_id": resource_a_id, "chunk_index": 0, "chunk_text": "A chunk",
    }).execute()
    admin.table("resource_chunks").insert({
        "resource_id": resource_b_id, "chunk_index": 0, "chunk_text": "B chunk",
    }).execute()

    # Workflows
    wf_a = admin.table("workflows").insert({
        "user_id": user_a_id, "goal_text": "A's workflow", "status": "queued",
    }).execute()
    wf_b = admin.table("workflows").insert({
        "user_id": user_b_id, "goal_text": "B's workflow", "status": "queued",
    }).execute()

    workflow_a_id = wf_a.data[0]["id"]
    workflow_b_id = wf_b.data[0]["id"]

    # Workflow snapshots
    admin.table("workflow_snapshots").insert({
        "workflow_id": workflow_a_id, "step_id": "signal_research", "state_json": {},
    }).execute()
    admin.table("workflow_snapshots").insert({
        "workflow_id": workflow_b_id, "step_id": "signal_research", "state_json": {},
    }).execute()

    # Content assets
    admin.table("content_assets").insert({
        "workflow_id": workflow_a_id, "type": "youtube_long", "content_json": {"text": "A script"},
    }).execute()
    admin.table("content_assets").insert({
        "workflow_id": workflow_b_id, "type": "youtube_long", "content_json": {"text": "B script"},
    }).execute()

    # Audit events
    admin.table("audit_events").insert({
        "user_id": user_a_id, "workflow_id": workflow_a_id,
        "event_type": "workflow_created", "payload": {},
    }).execute()
    admin.table("audit_events").insert({
        "user_id": user_b_id, "workflow_id": workflow_b_id,
        "event_type": "workflow_created", "payload": {},
    }).execute()

    # Usage costs
    admin.table("usage_costs").insert({
        "workflow_id": workflow_a_id, "user_id": user_a_id,
        "step_id": "signal_research", "model_name": "gpt-4o",
        "input_tokens": 100, "output_tokens": 50, "estimated_cost": 0.001,
    }).execute()
    admin.table("usage_costs").insert({
        "workflow_id": workflow_b_id, "user_id": user_b_id,
        "step_id": "signal_research", "model_name": "gpt-4o",
        "input_tokens": 200, "output_tokens": 100, "estimated_cost": 0.002,
    }).execute()

    return {
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "resource_a_id": resource_a_id,
        "resource_b_id": resource_b_id,
        "workflow_a_id": workflow_a_id,
        "workflow_b_id": workflow_b_id,
    }


# ── RLS Tests ─────────────────────────────────────────────────


class TestProfilesRLS:
    def test_user_a_sees_own_profile(self, client_a, seed_data):
        rows = client_a.table("profiles").select("*").execute()
        assert len(rows.data) == 1
        assert rows.data[0]["user_id"] == seed_data["user_a_id"]

    def test_user_a_cannot_see_user_b_profile(self, client_a, seed_data):
        rows = client_a.table("profiles").select("*").execute()
        user_ids = [r["user_id"] for r in rows.data]
        assert seed_data["user_b_id"] not in user_ids


class TestResourcesRLS:
    def test_user_a_sees_own_resources(self, client_a, seed_data):
        rows = client_a.table("resources").select("*").execute()
        assert len(rows.data) == 1
        assert rows.data[0]["title"] == "A's note"

    def test_user_a_cannot_see_user_b_resources(self, client_a, seed_data):
        rows = client_a.table("resources").select("*").execute()
        titles = [r["title"] for r in rows.data]
        assert "B's note" not in titles

    def test_user_b_sees_own_resources(self, client_b, seed_data):
        rows = client_b.table("resources").select("*").execute()
        assert len(rows.data) == 1
        assert rows.data[0]["title"] == "B's note"


class TestResourceChunksRLS:
    def test_user_a_sees_own_chunks(self, client_a, seed_data):
        rows = client_a.table("resource_chunks").select("*").execute()
        assert len(rows.data) == 1
        assert rows.data[0]["chunk_text"] == "A chunk"

    def test_user_a_cannot_see_user_b_chunks(self, client_a, seed_data):
        rows = client_a.table("resource_chunks").select("*").execute()
        texts = [r["chunk_text"] for r in rows.data]
        assert "B chunk" not in texts


class TestWorkflowsRLS:
    def test_user_a_sees_own_workflows(self, client_a, seed_data):
        rows = client_a.table("workflows").select("*").execute()
        assert len(rows.data) == 1
        assert rows.data[0]["goal_text"] == "A's workflow"

    def test_user_a_cannot_see_user_b_workflows(self, client_a, seed_data):
        rows = client_a.table("workflows").select("*").execute()
        goals = [r["goal_text"] for r in rows.data]
        assert "B's workflow" not in goals


class TestWorkflowSnapshotsRLS:
    def test_user_a_sees_own_snapshots(self, client_a, seed_data):
        rows = client_a.table("workflow_snapshots").select("*").execute()
        assert len(rows.data) == 1

    def test_user_a_cannot_see_user_b_snapshots(self, client_a, seed_data):
        rows = client_a.table("workflow_snapshots").select("*").execute()
        wf_ids = [r["workflow_id"] for r in rows.data]
        assert seed_data["workflow_b_id"] not in wf_ids


class TestContentAssetsRLS:
    def test_user_a_sees_own_assets(self, client_a, seed_data):
        rows = client_a.table("content_assets").select("*").execute()
        assert len(rows.data) == 1

    def test_user_a_cannot_see_user_b_assets(self, client_a, seed_data):
        rows = client_a.table("content_assets").select("*").execute()
        wf_ids = [r["workflow_id"] for r in rows.data]
        assert seed_data["workflow_b_id"] not in wf_ids


class TestAuditEventsRLS:
    def test_user_a_sees_own_events(self, client_a, seed_data):
        rows = client_a.table("audit_events").select("*").execute()
        assert len(rows.data) == 1

    def test_user_a_cannot_see_user_b_events(self, client_a, seed_data):
        rows = client_a.table("audit_events").select("*").execute()
        user_ids = [r["user_id"] for r in rows.data]
        assert seed_data["user_b_id"] not in user_ids


class TestUsageCostsRLS:
    def test_user_a_sees_own_costs(self, client_a, seed_data):
        rows = client_a.table("usage_costs").select("*").execute()
        assert len(rows.data) == 1

    def test_user_a_cannot_see_user_b_costs(self, client_a, seed_data):
        rows = client_a.table("usage_costs").select("*").execute()
        user_ids = [r["user_id"] for r in rows.data]
        assert seed_data["user_b_id"] not in user_ids


class TestUnauthenticatedAccess:
    """Anon client (no JWT) should see 0 rows on all tables."""

    def test_anon_sees_no_profiles(self):
        anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        rows = anon.table("profiles").select("*").execute()
        assert len(rows.data) == 0

    def test_anon_sees_no_workflows(self):
        anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        rows = anon.table("workflows").select("*").execute()
        assert len(rows.data) == 0

    def test_anon_sees_no_resources(self):
        anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        rows = anon.table("resources").select("*").execute()
        assert len(rows.data) == 0
