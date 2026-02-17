"""Tests for resource endpoints (Slice 5).

Verifies:
  - POST /resources creates a text resource (note, link, transcript)
  - POST /resources/upload handles file uploads with text extraction
  - GET /resources lists user resources with filtering
  - GET /resources/{id} returns resource with chunks
  - PATCH /resources/{id} updates title, tags, gold
  - DELETE /resources/{id} deletes resource + chunks
  - User isolation: User A cannot see User B's resources
  - Chunking produces expected chunk structure
  - File type validation rejects disallowed types
"""

import os
import uuid

import httpx
import pytest
from supabase import create_client

# ── Constants ─────────────────────────────────────────────

API_BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

TEST_USER_A_EMAIL = f"test-res-a-{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_B_EMAIL = f"test-res-b-{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "TestPassword123!"

SAMPLE_NOTE_TEXT = """This is a comprehensive guide to Python async programming.

Async programming in Python uses the asyncio library to run concurrent code.
The key concepts are: coroutines, event loops, tasks, and futures.

Coroutines are defined with async def and use await to yield control.
Event loops manage the execution of coroutines.
Tasks wrap coroutines and schedule them for execution.
Futures represent the eventual result of an async operation.

Best practices for async Python:
1. Use async context managers for resource cleanup.
2. Prefer asyncio.gather() for concurrent tasks.
3. Use asyncio.Queue for producer-consumer patterns.
4. Handle exceptions in gathered tasks carefully.
5. Avoid mixing sync and async code without proper bridges."""

LONG_TEXT = "A" * 5000  # Will produce multiple chunks


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture(scope="module")
def admin():
    """Supabase admin client (service role)."""
    assert SUPABASE_URL, "SUPABASE_URL not set"
    assert SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY not set"
    return create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


@pytest.fixture(scope="module")
def user_a(admin):
    """Create test user A and return (user_id, access_token)."""
    resp = admin.auth.admin.create_user({
        "email": TEST_USER_A_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = resp.user.id

    anon = create_client(SUPABASE_URL, os.environ.get("SUPABASE_ANON_KEY", ""))
    sign_in = anon.auth.sign_in_with_password({
        "email": TEST_USER_A_EMAIL,
        "password": TEST_PASSWORD,
    })
    token = sign_in.session.access_token

    yield user_id, token

    # Cleanup: delete user (cascades resources, chunks, etc.)
    try:
        admin.auth.admin.delete_user(user_id)
    except Exception:
        pass


@pytest.fixture(scope="module")
def user_b(admin):
    """Create test user B and return (user_id, access_token)."""
    resp = admin.auth.admin.create_user({
        "email": TEST_USER_B_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = resp.user.id

    anon = create_client(SUPABASE_URL, os.environ.get("SUPABASE_ANON_KEY", ""))
    sign_in = anon.auth.sign_in_with_password({
        "email": TEST_USER_B_EMAIL,
        "password": TEST_PASSWORD,
    })
    token = sign_in.session.access_token

    yield user_id, token

    try:
        admin.auth.admin.delete_user(user_id)
    except Exception:
        pass


# ── Test: POST /resources (note/link) ─────────────────────


class TestCreateResource:

    def test_create_note_success(self, user_a):
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "Python Async Guide",
                "content_text": SAMPLE_NOTE_TEXT,
                "tags": ["python", "async"],
                "is_gold": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "note"
        assert data["title"] == "Python Async Guide"
        assert data["chunk_count"] >= 1
        assert "id" in data

    def test_create_link_success(self, user_a):
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "link",
                "title": "LangGraph Docs",
                "content_text": "LangGraph is a library for building stateful AI agents.",
                "source_url": "https://langchain-ai.github.io/langgraph/",
                "tags": ["langgraph", "docs"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "link"

    def test_create_note_no_auth(self):
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "No auth test", "content_text": "Should fail"},
        )
        assert resp.status_code == 401

    def test_create_note_invalid_type(self, user_a):
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "invalid_type", "title": "Bad type", "content_text": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_create_note_gold(self, user_a):
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "Gold Resource Test",
                "content_text": "This is a gold reference resource.",
                "tags": ["hooks"],
                "is_gold": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    def test_create_note_chunks_long_text(self, user_a):
        """Long text should produce multiple chunks."""
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "Long Text Chunking Test",
                "content_text": LONG_TEXT,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["chunk_count"] >= 2  # 5000 chars / ~2000 chunk size


# ── Test: POST /resources/upload (file) ───────────────────


class TestUploadResource:

    def test_upload_txt_file(self, user_a):
        _, token = user_a
        file_content = b"This is a test text file with sample content for ingestion."
        resp = httpx.post(
            f"{API_BASE}/resources/upload",
            params={"title": "Test TXT Upload", "tags": "test,upload"},
            files={"file": ("test.txt", file_content, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "file"
        assert data["title"] == "Test TXT Upload"
        assert data["chunk_count"] >= 1

    def test_upload_md_file(self, user_a):
        _, token = user_a
        md_content = b"# Header\n\nThis is markdown content.\n\n## Subheader\n\nMore text here."
        resp = httpx.post(
            f"{API_BASE}/resources/upload",
            params={"title": "Test MD Upload"},
            files={"file": ("notes.md", md_content, "text/markdown")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    def test_upload_csv_file(self, user_a):
        _, token = user_a
        csv_content = b"topic,score,source\nAI agents,85,YouTube\nLangGraph,92,Reddit"
        resp = httpx.post(
            f"{API_BASE}/resources/upload",
            params={"title": "Research Data CSV"},
            files={"file": ("data.csv", csv_content, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    def test_upload_disallowed_type(self, user_a):
        _, token = user_a
        resp = httpx.post(
            f"{API_BASE}/resources/upload",
            params={"title": "Bad File Type"},
            files={"file": ("script.exe", b"binary", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_upload_no_auth(self):
        resp = httpx.post(
            f"{API_BASE}/resources/upload",
            params={"title": "No Auth Upload"},
            files={"file": ("test.txt", b"content", "text/plain")},
        )
        assert resp.status_code == 401


# ── Test: GET /resources ──────────────────────────────────


class TestListResources:

    def test_list_returns_own_resources(self, user_a):
        _, token = user_a
        resp = httpx.get(
            f"{API_BASE}/resources",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_filter_by_tag(self, user_a):
        _, token = user_a
        resp = httpx.get(
            f"{API_BASE}/resources",
            params={"tag": "python"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert "python" in r["tags"]

    def test_list_filter_by_gold(self, user_a):
        _, token = user_a
        resp = httpx.get(
            f"{API_BASE}/resources",
            params={"is_gold": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["is_gold"] is True

    def test_list_no_auth(self):
        resp = httpx.get(f"{API_BASE}/resources")
        assert resp.status_code == 401

    def test_list_user_isolation(self, user_a, user_b):
        """User B should NOT see User A's resources."""
        _, token_a = user_a
        _, token_b = user_b

        # Create a resource as user A with distinctive title
        httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "UserA-Isolation-Resource-XXXYYY",
                "content_text": "This belongs to user A only.",
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # List as user B
        resp_b = httpx.get(
            f"{API_BASE}/resources",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 200
        for r in resp_b.json():
            assert "UserA-Isolation-Resource-XXXYYY" not in r["title"]


# ── Test: GET /resources/{id} ─────────────────────────────


class TestGetResource:

    def test_get_resource_with_chunks(self, user_a):
        _, token = user_a

        # Create a resource first
        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "Resource Detail Test",
                "content_text": SAMPLE_NOTE_TEXT,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        # Get detail
        resp = httpx.get(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == resource_id
        assert data["title"] == "Resource Detail Test"
        assert data["content_text"] == SAMPLE_NOTE_TEXT
        assert len(data["chunks"]) >= 1
        # Chunks should be ordered by chunk_index
        for i, chunk in enumerate(data["chunks"]):
            assert chunk["chunk_index"] == i
            assert len(chunk["chunk_text"]) > 0

    def test_get_resource_not_found(self, user_a):
        _, token = user_a
        fake_id = str(uuid.uuid4())
        resp = httpx.get(
            f"{API_BASE}/resources/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_get_resource_other_user_returns_404(self, user_a, user_b):
        _, token_a = user_a
        _, token_b = user_b

        # Create as user A
        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "Cross-user access test",
                "content_text": "Should not be visible to user B.",
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        resource_id = create_resp.json()["id"]

        # Try to access as user B
        resp = httpx.get(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404


# ── Test: PATCH /resources/{id} ───────────────────────────


class TestUpdateResource:

    def test_update_title(self, user_a):
        _, token = user_a

        # Create resource
        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Original Title", "content_text": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        # Update title
        resp = httpx.patch(
            f"{API_BASE}/resources/{resource_id}",
            json={"title": "Updated Title"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_toggle_gold(self, user_a):
        _, token = user_a

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Gold Toggle Test", "content_text": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        # Toggle gold on
        resp = httpx.patch(
            f"{API_BASE}/resources/{resource_id}",
            json={"is_gold": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_gold"] is True

    def test_update_tags(self, user_a):
        _, token = user_a

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Tags Test", "content_text": "Test", "tags": ["old"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        resp = httpx.patch(
            f"{API_BASE}/resources/{resource_id}",
            json={"tags": ["new", "updated"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "new" in resp.json()["tags"]
        assert "updated" in resp.json()["tags"]

    def test_update_other_user_returns_404(self, user_a, user_b):
        _, token_a = user_a
        _, token_b = user_b

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Cross-user update", "content_text": "Test"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        resource_id = create_resp.json()["id"]

        resp = httpx.patch(
            f"{API_BASE}/resources/{resource_id}",
            json={"title": "Hacked"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    def test_update_empty_body(self, user_a):
        _, token = user_a

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Empty Update Test", "content_text": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        resp = httpx.patch(
            f"{API_BASE}/resources/{resource_id}",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400


# ── Test: DELETE /resources/{id} ──────────────────────────


class TestDeleteResource:

    def test_delete_resource_success(self, user_a, admin):
        _, token = user_a

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={
                "type": "note",
                "title": "To Be Deleted",
                "content_text": "This resource will be deleted.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resource_id = create_resp.json()["id"]

        # Verify chunks exist before delete
        chunks_before = (
            admin.table("resource_chunks")
            .select("id")
            .eq("resource_id", resource_id)
            .execute()
        )
        assert len(chunks_before.data) >= 1

        # Delete
        resp = httpx.delete(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        # Verify resource is gone
        get_resp = httpx.get(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 404

        # Verify chunks are gone
        chunks_after = (
            admin.table("resource_chunks")
            .select("id")
            .eq("resource_id", resource_id)
            .execute()
        )
        assert len(chunks_after.data) == 0

    def test_delete_not_found(self, user_a):
        _, token = user_a
        fake_id = str(uuid.uuid4())
        resp = httpx.delete(
            f"{API_BASE}/resources/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_delete_other_user_returns_404(self, user_a, user_b):
        _, token_a = user_a
        _, token_b = user_b

        create_resp = httpx.post(
            f"{API_BASE}/resources",
            json={"type": "note", "title": "Cross-user delete", "content_text": "Test"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        resource_id = create_resp.json()["id"]

        # User B tries to delete User A's resource
        resp = httpx.delete(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

        # Verify it still exists for User A
        get_resp = httpx.get(
            f"{API_BASE}/resources/{resource_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert get_resp.status_code == 200
