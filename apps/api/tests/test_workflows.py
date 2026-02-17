"""Tests for workflow endpoints (Slices 7-10).

Tests cover:
  - Workflow schema validation (platforms, settings)
  - Brand completeness gate
  - Workflow CRUD endpoints
  - Topic/hook selection
  - Content asset endpoints
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Schema Tests ─────────────────────────────────────────────


class TestWorkflowSchemas:
    """Verify Pydantic models accept valid data and enforce constraints."""

    def test_workflow_create_defaults(self):
        from app.schemas.workflow import WorkflowCreate
        wf = WorkflowCreate(goal_text="Create content about personal branding")
        assert wf.platforms == ["youtube"]
        assert "sources" in wf.settings

    def test_workflow_create_with_platforms(self):
        from app.schemas.workflow import WorkflowCreate
        wf = WorkflowCreate(
            goal_text="Create content about AI tools for business",
            platforms=["youtube", "linkedin", "twitter"],
        )
        assert len(wf.platforms) == 3
        assert "linkedin" in wf.platforms

    def test_workflow_create_min_length(self):
        from app.schemas.workflow import WorkflowCreate
        with pytest.raises(Exception):
            WorkflowCreate(goal_text="short")

    def test_workflow_summary_includes_platforms(self):
        from app.schemas.workflow import WorkflowSummary
        from datetime import datetime
        summary = WorkflowSummary(
            id="test-id",
            status="queued",
            goal_text="Test workflow",
            active_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            platforms=["youtube", "linkedin"],
        )
        assert summary.platforms == ["youtube", "linkedin"]

    def test_workflow_summary_default_platforms(self):
        from app.schemas.workflow import WorkflowSummary
        from datetime import datetime
        summary = WorkflowSummary(
            id="test-id",
            status="queued",
            goal_text="Test workflow",
            active_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert summary.platforms == ["youtube"]

    def test_content_asset_schema(self):
        from app.schemas.workflow import ContentAsset
        from datetime import datetime
        asset = ContentAsset(
            id="asset-1",
            workflow_id="wf-1",
            asset_type="youtube_long",
            platform="youtube",
            title="Test Script",
            body={"sections": []},
            version=1,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert asset.asset_type == "youtube_long"
        assert asset.platform == "youtube"

    def test_valid_platforms_constant(self):
        from app.schemas.workflow import VALID_PLATFORMS
        assert "youtube" in VALID_PLATFORMS
        assert "linkedin" in VALID_PLATFORMS
        assert "twitter" in VALID_PLATFORMS
        assert "short_form" in VALID_PLATFORMS


# ── API Endpoint Tests ───────────────────────────────────────


class TestWorkflowEndpoints:
    """Test workflow API endpoints using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client with auth override."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user

        class FakeUser:
            id = "test-user-123"
            email = "test@example.com"

        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    @patch("app.routers.usage.check_daily_workflow_cap", return_value={"used": 0, "cap": 10, "remaining": 10, "at_limit": False})
    @patch("app.routers.workflows.get_admin_client")
    def test_create_workflow_brand_gate_blocks_incomplete(self, mock_admin, _mock_cap):
        """Should reject workflow creation when brand profile is < 50% complete."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # Profile with only 1 of 4 sections filled (25%)
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"profile_json": {"foundation": {"beliefs": "test", "it_factor": "test"}}}]
        )

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding strategies",
            "platforms": ["youtube"],
        })
        assert resp.status_code == 400
        assert "25% complete" in resp.json()["detail"]

    @patch("app.routers.usage.check_daily_workflow_cap", return_value={"used": 0, "cap": 10, "remaining": 10, "at_limit": False})
    @patch("app.routers.workflows.get_admin_client")
    def test_create_workflow_brand_gate_allows_complete(self, mock_admin, _mock_cap):
        """Should allow workflow creation when brand profile >= 50% complete."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # Profile with 3 of 4 sections filled (75%)
        profile = {
            "foundation": {"beliefs": "test", "it_factor": "test"},
            "ica": {"big_need": "test", "big_want": "test"},
            "offer": {"what": "test", "target_audience": "test"},
        }

        # For select().eq() calls, we chain
        select_mock = MagicMock()
        mock_client.table.return_value.select.return_value = select_mock
        select_mock.eq.return_value.execute.return_value = MagicMock(
            data=[{"profile_json": profile}]
        )

        # For insert() call (workflow creation and audit)
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "wf-new-123",
                "status": "queued",
                "user_id": "test-user-123",
                "goal_text": "Create content about personal branding strategies",
                "settings": {"platforms": ["youtube"]},
            }]
        )

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding strategies",
            "platforms": ["youtube"],
        })
        assert resp.status_code == 201
        assert resp.json()["id"] == "wf-new-123"

    @patch("app.routers.workflows.get_admin_client")
    def test_create_workflow_invalid_platform(self, mock_admin):
        """Should reject invalid platform names."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # Profile with enough data to pass brand gate
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"profile_json": {
                "foundation": {"beliefs": "test", "it_factor": "test"},
                "ica": {"big_need": "test", "big_want": "test"},
            }}]
        )

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding strategies",
            "platforms": ["youtube", "tiktok_live"],
        })
        assert resp.status_code == 422
        assert "Invalid platforms" in resp.json()["detail"]

    @patch("app.routers.workflows.get_admin_client")
    def test_create_workflow_empty_platforms(self, mock_admin):
        """Should reject empty platforms list."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"profile_json": {
                "foundation": {"beliefs": "test", "it_factor": "test"},
                "ica": {"big_need": "test", "big_want": "test"},
            }}]
        )

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding strategies",
            "platforms": [],
        })
        assert resp.status_code == 422
        assert "At least one platform" in resp.json()["detail"]

    @patch("app.routers.workflows.get_admin_client")
    def test_list_workflows(self, mock_admin):
        """Should return list of workflows with platforms."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "wf-1",
                    "status": "completed",
                    "goal_text": "Test workflow",
                    "current_step": "approval",
                    "active_version": 1,
                    "settings": {"platforms": ["youtube", "linkedin"]},
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T12:00:00",
                }
            ]
        )

        resp = self.client.get("/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["platforms"] == ["youtube", "linkedin"]

    @patch("app.routers.workflows.get_admin_client")
    def test_get_workflow_assets(self, mock_admin):
        """Should return content assets for a workflow."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # First call: verify ownership
        ownership_mock = MagicMock()
        ownership_mock.data = [{"id": "wf-1"}]

        # Second call: get assets
        assets_mock = MagicMock()
        assets_mock.data = [
            {
                "id": "asset-1",
                "workflow_id": "wf-1",
                "asset_type": "youtube_long",
                "platform": "youtube",
                "title": "Test Script",
                "body": {"sections": []},
                "version": 1,
                "status": "draft",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            }
        ]

        # Chain the mock calls
        table_mock = MagicMock()
        mock_client.table.return_value = table_mock

        # The router calls table().select().eq().eq().execute() for ownership
        # then table().select().eq().order().execute() for assets
        eq_chain = MagicMock()
        eq_chain.eq.return_value.execute.return_value = ownership_mock
        table_mock.select.return_value.eq.return_value = eq_chain

        # For the second call, override the order chain
        eq_chain.order.return_value.execute.return_value = assets_mock

        resp = self.client.get("/workflows/wf-1/assets")
        assert resp.status_code == 200


# ── Export Tests ──────────────────────────────────────────────


class TestExportHelpers:
    """Verify content formatting helpers work correctly."""

    def test_format_content_as_text_youtube(self):
        from app.routers.workflows import _format_content_as_text

        pack = {
            "youtube_long": {
                "hook": "Did you know that 90% of brands fail?",
                "sections": [
                    {"timestamp": "0:00", "heading": "Intro", "script": "Welcome to the video."},
                    {"timestamp": "2:00", "heading": "Main Point", "script": "Here is the key insight."},
                ],
            },
            "titles": ["Brand Building 101", "How to Build Your Brand"],
            "description": "A video about brand building",
            "tags": ["branding", "marketing"],
            "pinned_comment": "Drop a comment below!",
        }
        text = _format_content_as_text(pack)
        assert "YOUTUBE LONG-FORM SCRIPT" in text
        assert "Did you know that 90% of brands fail?" in text
        assert "[0:00] Intro" in text
        assert "TITLE OPTIONS:" in text
        assert "Brand Building 101" in text
        assert "DESCRIPTION:" in text
        assert "TAGS:" in text
        assert "PINNED COMMENT:" in text

    def test_format_content_as_text_multiplatform(self):
        from app.routers.workflows import _format_content_as_text

        pack = {
            "linkedin_posts": [
                {"post_type": "story", "hook_line": "Here is what I learned", "body": "A lesson about growth.", "cta": "Follow for more."},
            ],
            "twitter_posts": [
                {"angle": "hot_take", "tweet_text": "Hot take: brand is everything."},
            ],
            "short_form_scripts": [
                {"angle": "story", "hook": "Stop scrolling.", "script": "Here is the thing.", "punchline": "And that changed everything.", "cta": "Follow!"},
            ],
        }
        text = _format_content_as_text(pack)
        assert "LINKEDIN POSTS" in text
        assert "Here is what I learned" in text
        assert "TWITTER/X POSTS" in text
        assert "brand is everything" in text
        assert "SHORT-FORM SCRIPTS" in text
        assert "Stop scrolling." in text

    def test_format_content_as_markdown(self):
        from app.routers.workflows import _format_content_as_markdown

        pack = {
            "youtube_long": {
                "hook": "Hook line here",
                "sections": [
                    {"timestamp": "0:00", "heading": "Intro", "script": "Welcome."},
                ],
            },
            "titles": ["Title One"],
        }
        md = _format_content_as_markdown(pack, goal_text="Test Goal")
        assert "# Content Pack: Test Goal" in md
        assert "## YouTube Long-Form Script" in md
        assert "### Hook" in md
        assert "### Title Options" in md

    def test_format_empty_pack(self):
        from app.routers.workflows import _format_content_as_text, _format_content_as_markdown

        text = _format_content_as_text({})
        md = _format_content_as_markdown({})
        # Should not crash, just return minimal content
        assert isinstance(text, str)
        assert isinstance(md, str)
        assert "# Content Pack" in md
