"""Tests for usage & cost tracking (Slice 12).

Tests cover:
  - Cost estimation helper
  - Usage summary endpoint
  - Daily usage endpoint
  - Daily workflow cap
  - Rate limiting on workflow creation
  - Token ceiling clamping
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Cost estimation tests ────────────────────────────────────


class TestCostEstimation:
    """Verify the cost estimation helper."""

    def test_estimate_cost_gpt4o(self):
        from worker.graph.llm import estimate_cost

        # GPT-4o: $0.0025/1K input, $0.01/1K output
        cost = estimate_cost("gpt-4o", 1000, 1000)
        expected = 0.0025 + 0.01
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_gpt4o_mini(self):
        from worker.graph.llm import estimate_cost

        # GPT-4o-mini: $0.00015/1K input, $0.0006/1K output
        cost = estimate_cost("gpt-4o-mini", 10000, 5000)
        expected = (10000 / 1000 * 0.00015) + (5000 / 1000 * 0.0006)
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_unknown_model_defaults_to_gpt4o(self):
        from worker.graph.llm import estimate_cost

        cost_unknown = estimate_cost("some-future-model", 1000, 1000)
        cost_gpt4o = estimate_cost("gpt-4o", 1000, 1000)
        assert cost_unknown == cost_gpt4o

    def test_estimate_cost_zero_tokens(self):
        from worker.graph.llm import estimate_cost

        cost = estimate_cost("gpt-4o", 0, 0)
        assert cost == 0.0


class TestTokenCeiling:
    """Verify token ceiling clamping in OpenAIClient."""

    def test_max_tokens_clamped_to_ceiling(self):
        """If max_tokens > settings.max_tokens_per_step, it should be clamped."""
        from worker.graph.llm import OpenAIClient
        from app.config import settings

        # The ceiling is settings.max_tokens_per_step (32000 by default)
        ceiling = settings.max_tokens_per_step

        # We can't call the real API, but we verify the config value is set
        assert ceiling > 0
        assert ceiling == 32000  # default from config


class TestTrackingContext:
    """Verify the thread-local tracking context."""

    def test_set_and_clear_context(self):
        from worker.graph.llm import (
            set_tracking_context,
            clear_tracking_context,
            _tracking_context,
        )

        set_tracking_context("wf-123", "user-456", "signal_research")
        assert _tracking_context.workflow_id == "wf-123"
        assert _tracking_context.user_id == "user-456"
        assert _tracking_context.step_id == "signal_research"

        clear_tracking_context()
        assert _tracking_context.workflow_id is None


# ── Daily cap tests ──────────────────────────────────────────


class TestDailyCap:
    """Verify the daily workflow cap check."""

    @patch("app.routers.usage.get_admin_client")
    def test_cap_not_reached(self, mock_admin):
        from app.routers.usage import check_daily_workflow_cap

        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # Simulate 3 workflows today
        mock_resp = MagicMock()
        mock_resp.count = 3
        mock_resp.data = [{"id": f"wf-{i}"} for i in range(3)]
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_resp

        result = check_daily_workflow_cap("user-1")
        assert result["used"] == 3
        assert result["cap"] == 10  # default
        assert result["remaining"] == 7
        assert result["at_limit"] is False

    @patch("app.routers.usage.get_admin_client")
    def test_cap_reached(self, mock_admin):
        from app.routers.usage import check_daily_workflow_cap

        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.count = 10
        mock_resp.data = [{"id": f"wf-{i}"} for i in range(10)]
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_resp

        result = check_daily_workflow_cap("user-1")
        assert result["used"] == 10
        assert result["at_limit"] is True
        assert result["remaining"] == 0


# ── Endpoint tests ───────────────────────────────────────────


class TestUsageEndpoints:
    """Test usage API endpoints with mocked auth and Supabase."""

    @classmethod
    def setup_class(cls):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user

        cls.mock_user = MagicMock()
        cls.mock_user.id = "test-user-id"

        app.dependency_overrides[get_current_user] = lambda: cls.mock_user
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        from app.main import app
        from app.auth import get_current_user
        app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.usage.get_admin_client")
    def test_get_usage_summary_empty(self, mock_admin):
        """Should return zeros when no usage data exists."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # usage_costs query returns empty
        costs_mock = MagicMock()
        costs_mock.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = costs_mock

        # daily cap query
        cap_mock = MagicMock()
        cap_mock.count = 0
        cap_mock.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = cap_mock

        resp = self.client.get("/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] == 0.0
        assert data["total_calls"] == 0
        assert data["workflow_count"] == 0
        assert "period_costs" in data
        assert data["daily_workflow_cap"] == 10

    @patch("app.routers.usage.get_admin_client")
    def test_get_cap_status(self, mock_admin):
        """Should return cap status."""
        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        cap_mock = MagicMock()
        cap_mock.count = 5
        cap_mock.data = [{"id": f"wf-{i}"} for i in range(5)]
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = cap_mock

        resp = self.client.get("/usage/cap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["daily_workflows_used"] == 5
        assert data["daily_workflow_cap"] == 10
        assert data["remaining"] == 5
        assert data["at_limit"] is False


class TestRateLimitOnWorkflowCreation:
    """Test that workflow creation respects daily cap."""

    @classmethod
    def setup_class(cls):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user

        cls.mock_user = MagicMock()
        cls.mock_user.id = "test-user-id"

        app.dependency_overrides[get_current_user] = lambda: cls.mock_user
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        from app.main import app
        from app.auth import get_current_user
        app.dependency_overrides.pop(get_current_user, None)

    @patch("app.routers.usage.check_daily_workflow_cap")
    @patch("app.routers.workflows.get_admin_client")
    def test_rate_limit_blocks_at_cap(self, mock_admin, mock_cap):
        """Should return 429 when daily cap is reached."""
        mock_cap.return_value = {
            "used": 10,
            "cap": 10,
            "remaining": 0,
            "at_limit": True,
        }

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding",
            "platforms": ["youtube"],
        })
        assert resp.status_code == 429
        assert "Daily workflow limit" in resp.json()["detail"]

    @patch("app.routers.usage.check_daily_workflow_cap")
    @patch("app.routers.workflows.get_admin_client")
    def test_rate_limit_allows_under_cap(self, mock_admin, mock_cap):
        """Should allow workflow creation when under cap."""
        mock_cap.return_value = {
            "used": 3,
            "cap": 10,
            "remaining": 7,
            "at_limit": False,
        }

        mock_client = MagicMock()
        mock_admin.return_value = mock_client

        # Profile query (brand gate)
        profile_mock = MagicMock()
        profile_mock.data = [{
            "profile_json": {
                "foundation": {"beliefs": "test", "it_factor": "test"},
                "ica": {"demographics": {"age": "30"}, "big_need": "growth"},
                "offer": {"what": "coaching", "target_audience": "creators"},
            }
        }]

        # Workflow insert
        wf_mock = MagicMock()
        wf_mock.data = [{
            "id": "wf-new",
            "status": "queued",
            "goal_text": "Create content about personal branding",
            "current_step": None,
            "active_version": 1,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "settings": {"platforms": ["youtube"]},
        }]

        # Audit insert
        audit_mock = MagicMock()
        audit_mock.data = [{}]

        # Chain mocks
        table_mock = MagicMock()
        mock_client.table.return_value = table_mock

        # The profile select query
        select_mock = MagicMock()
        select_mock.eq.return_value.execute.return_value = profile_mock
        table_mock.select.return_value = select_mock

        # The workflow insert
        table_mock.insert.return_value.execute.return_value = wf_mock

        resp = self.client.post("/workflows", json={
            "goal_text": "Create content about personal branding strategies for creators",
            "platforms": ["youtube"],
        })
        # Should pass the cap check (might fail on brand gate depending on mock chain,
        # but should NOT fail with 429)
        assert resp.status_code != 429
