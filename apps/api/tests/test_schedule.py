"""Tests for schedule endpoints (Kanban + Calendar).

Tests cover:
  - Schema validation
  - Create / list / update / move / delete operations
  - Import from workflow
  - Calendar date filtering
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from app.main import app
from app.auth import get_current_user


# ── Fake user for auth override ─────────────────────────────

class FakeUser:
    id = "test-schedule-user-001"
    email = "schedule@test.com"


# ── Helper to build mock Supabase client ──────────────────────

def _mock_admin():
    """Build a mock Supabase admin client with chainable methods."""
    mock_client = MagicMock()

    def _chain(data=None):
        """Return a mock that supports .select().eq().order()... chains."""
        m = MagicMock()
        m.execute.return_value = MagicMock(data=data or [])
        m.select.return_value = m
        m.eq.return_value = m
        m.gte.return_value = m
        m.lte.return_value = m
        m.in_.return_value = m
        m.not_.return_value = m
        m.is_.return_value = m
        m.order.return_value = m
        m.limit.return_value = m
        m.insert.return_value = m
        m.update.return_value = m
        m.delete.return_value = m
        return m

    mock_client.table.return_value = _chain()
    return mock_client


# ── Schema tests ─────────────────────────────────────────────

class TestScheduleSchemas:
    """Validate Pydantic models used by the schedule router."""

    def test_scheduled_item_create_minimal(self):
        from app.routers.schedule import ScheduledItemCreate
        item = ScheduledItemCreate(title="Test post")
        assert item.title == "Test post"
        assert item.platform == "other"
        assert item.status == "draft"

    def test_scheduled_item_create_full(self):
        from app.routers.schedule import ScheduledItemCreate
        item = ScheduledItemCreate(
            title="My YouTube Video",
            platform="youtube",
            content_type="youtube_long",
            status="scheduled",
            scheduled_at="2026-03-01T10:00:00Z",
            color_label="blue",
            notes="Remember to add thumbnail",
            workflow_id="wf-123",
        )
        assert item.platform == "youtube"
        assert item.scheduled_at == "2026-03-01T10:00:00Z"

    def test_move_request(self):
        from app.routers.schedule import MoveRequest
        mv = MoveRequest(status="published", column_order=2)
        assert mv.status == "published"
        assert mv.column_order == 2

    def test_kanban_board_model(self):
        from app.routers.schedule import KanbanBoard
        board = KanbanBoard(draft=[], scheduled=[], published=[], archived=[])
        assert len(board.draft) == 0


# ── CRUD endpoint tests ──────────────────────────────────────

class TestScheduleEndpoints:
    """Test the schedule API endpoints with mocked Supabase."""

    @pytest.fixture(autouse=True)
    def setup(self):
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    @patch("app.routers.schedule.get_admin_client")
    def test_get_kanban_board_empty(self, mock_admin):
        mc = _mock_admin()
        mock_admin.return_value = mc
        resp = self.client.get("/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert "draft" in data
        assert "scheduled" in data
        assert "published" in data
        assert "archived" in data

    @patch("app.routers.schedule.get_admin_client")
    def test_get_kanban_board_with_items(self, mock_admin):
        mc = _mock_admin()
        mc.table.return_value.execute.return_value = MagicMock(data=[
            {"id": "1", "user_id": "test-schedule-user-001", "title": "Draft post",
             "platform": "youtube", "content_type": "youtube_long", "status": "draft",
             "column_order": 0, "created_at": "2026-01-01T00:00:00Z",
             "updated_at": "2026-01-01T00:00:00Z", "body_preview": None,
             "content_json": {}, "workflow_id": None, "asset_id": None,
             "content_post_id": None, "scheduled_at": None, "published_at": None,
             "published_url": None, "color_label": None, "notes": None},
            {"id": "2", "user_id": "test-schedule-user-001", "title": "Scheduled tweet",
             "platform": "twitter", "content_type": "twitter_post", "status": "scheduled",
             "column_order": 0, "created_at": "2026-01-01T00:00:00Z",
             "updated_at": "2026-01-01T00:00:00Z", "body_preview": "Thread about AI",
             "content_json": {}, "workflow_id": None, "asset_id": None,
             "content_post_id": None, "scheduled_at": "2026-03-01T10:00:00Z",
             "published_at": None, "published_url": None, "color_label": "blue",
             "notes": None},
        ])
        mock_admin.return_value = mc

        resp = self.client.get("/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["draft"]) == 1
        assert len(data["scheduled"]) == 1
        assert data["draft"][0]["title"] == "Draft post"
        assert data["scheduled"][0]["color_label"] == "blue"

    @patch("app.routers.schedule.get_admin_client")
    def test_create_item_minimal(self, mock_admin):
        mc = _mock_admin()
        # Mock the order lookup
        mc.table.return_value.execute.return_value = MagicMock(data=[])
        # Mock insert
        insert_result = MagicMock(data=[{
            "id": "new-item-1", "user_id": "test-schedule-user-001",
            "title": "New blog post", "platform": "other", "content_type": "note",
            "body_preview": None, "content_json": {}, "workflow_id": None,
            "asset_id": None, "content_post_id": None, "status": "draft",
            "column_order": 0, "scheduled_at": None, "published_at": None,
            "published_url": None, "color_label": None, "notes": None,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        }])
        mc.table.return_value.insert.return_value.execute.return_value = insert_result
        mock_admin.return_value = mc

        resp = self.client.post("/schedule", json={"title": "New blog post"})
        assert resp.status_code == 201
        assert resp.json()["title"] == "New blog post"

    @patch("app.routers.schedule.get_admin_client")
    def test_create_item_invalid_status(self, mock_admin):
        mc = _mock_admin()
        mock_admin.return_value = mc
        resp = self.client.post("/schedule", json={
            "title": "Bad status",
            "status": "nonexistent",
        })
        assert resp.status_code == 422

    @patch("app.routers.schedule.get_admin_client")
    def test_update_item(self, mock_admin):
        mc = _mock_admin()
        # Mock ownership check
        mc.table.return_value.execute.return_value = MagicMock(data=[{"id": "item-1"}])
        # Mock update
        update_result = MagicMock(data=[{
            "id": "item-1", "user_id": "test-schedule-user-001",
            "title": "Updated title", "platform": "youtube", "content_type": "youtube_long",
            "body_preview": None, "content_json": {}, "workflow_id": None,
            "asset_id": None, "content_post_id": None, "status": "draft",
            "column_order": 0, "scheduled_at": None, "published_at": None,
            "published_url": None, "color_label": None, "notes": "added note",
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z",
        }])
        mc.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = update_result
        mock_admin.return_value = mc

        resp = self.client.patch("/schedule/item-1", json={
            "title": "Updated title",
            "notes": "added note",
        })
        assert resp.status_code == 200

    @patch("app.routers.schedule.get_admin_client")
    def test_update_item_not_found(self, mock_admin):
        mc = _mock_admin()
        mc.table.return_value.execute.return_value = MagicMock(data=[])
        mock_admin.return_value = mc

        resp = self.client.patch("/schedule/nonexistent", json={"title": "x"})
        assert resp.status_code == 404

    @patch("app.routers.schedule.get_admin_client")
    def test_move_item(self, mock_admin):
        mc = _mock_admin()
        # Mock ownership check
        mc.table.return_value.execute.return_value = MagicMock(data=[
            {"id": "item-1", "status": "draft"}
        ])
        # Mock update
        move_result = MagicMock(data=[{
            "id": "item-1", "user_id": "test-schedule-user-001",
            "title": "My post", "platform": "youtube", "content_type": "youtube_long",
            "body_preview": None, "content_json": {}, "workflow_id": None,
            "asset_id": None, "content_post_id": None, "status": "scheduled",
            "column_order": 0, "scheduled_at": None, "published_at": None,
            "published_url": None, "color_label": None, "notes": None,
            "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z",
        }])
        mc.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = move_result
        mock_admin.return_value = mc

        resp = self.client.patch("/schedule/item-1/move", json={
            "status": "scheduled",
            "column_order": 0,
        })
        assert resp.status_code == 200

    @patch("app.routers.schedule.get_admin_client")
    def test_move_item_invalid_status(self, mock_admin):
        mc = _mock_admin()
        mock_admin.return_value = mc
        resp = self.client.patch("/schedule/item-1/move", json={
            "status": "invalid",
            "column_order": 0,
        })
        assert resp.status_code == 422

    @patch("app.routers.schedule.get_admin_client")
    def test_delete_item(self, mock_admin):
        mc = _mock_admin()
        mc.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "item-1"}]
        )
        mock_admin.return_value = mc

        resp = self.client.delete("/schedule/item-1")
        assert resp.status_code == 204

    @patch("app.routers.schedule.get_admin_client")
    def test_delete_item_not_found(self, mock_admin):
        mc = _mock_admin()
        mc.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_admin.return_value = mc

        resp = self.client.delete("/schedule/nonexistent")
        assert resp.status_code == 404


# ── Calendar endpoint tests ──────────────────────────────────

class TestCalendarEndpoints:
    """Test calendar date range queries."""

    @pytest.fixture(autouse=True)
    def setup(self):
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    @patch("app.routers.schedule.get_admin_client")
    def test_calendar_returns_items_in_range(self, mock_admin):
        mc = MagicMock()
        # Build a fully chainable mock where every method returns the same object
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.not_ = chain  # not_ is accessed as property, not called
        chain.is_.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.execute.return_value = MagicMock(data=[
            {"id": "1", "title": "Monday post", "scheduled_at": "2026-03-02T10:00:00Z",
             "platform": "linkedin", "content_type": "linkedin_post",
             "status": "scheduled", "column_order": 0},
        ])
        mc.table.return_value = chain
        mock_admin.return_value = mc

        resp = self.client.get("/schedule/calendar?start=2026-03-01T00:00:00Z&end=2026-03-31T23:59:59Z")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Monday post"

    @patch("app.routers.schedule.get_admin_client")
    def test_calendar_requires_start_and_end(self, mock_admin):
        mc = _mock_admin()
        mock_admin.return_value = mc
        resp = self.client.get("/schedule/calendar")
        assert resp.status_code == 422  # Missing required query params


# ── Import from workflow tests ────────────────────────────────

class TestImportFromWorkflow:
    """Test importing content from an approved workflow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    @patch("app.routers.schedule.get_admin_client")
    def test_import_no_workflow_found(self, mock_admin):
        mc = _mock_admin()
        # Workflow not found
        mc.table.return_value.execute.return_value = MagicMock(data=[])
        mock_admin.return_value = mc

        resp = self.client.post("/schedule/import/nonexistent-wf")
        assert resp.status_code == 404

    @patch("app.routers.schedule.get_admin_client")
    def test_import_no_content_in_workflow(self, mock_admin):
        mc = MagicMock()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.in_.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.insert.return_value = chain

            if call_count["n"] == 1:
                # workflow found
                chain.execute.return_value = MagicMock(data=[{
                    "id": "wf-1", "goal_text": "Test", "settings": {}, "status": "approved",
                }])
            else:
                # No snapshots
                chain.execute.return_value = MagicMock(data=[])
            return chain

        mc.table.side_effect = side_effect
        mock_admin.return_value = mc

        resp = self.client.post("/schedule/import/wf-1")
        assert resp.status_code == 404
        assert "No content found" in resp.json()["detail"]
