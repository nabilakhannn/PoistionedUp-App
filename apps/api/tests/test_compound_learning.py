"""Tests for Slice 25: Compound Learning Loop.

Covers:
  - record_workflow_memories() auto-memory creation
  - Advisor suggestion generation (rule-based fallback)
  - Advisor router endpoint
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_current_user


# ── Fixtures ────────────────────────────────────────────────

class FakeUser:
    id = "user-test-123"
    email = "test@example.com"


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── record_workflow_memories tests ──────────────────────────


class TestRecordWorkflowMemories:
    """Test auto-memory creation after workflow approval."""

    @patch("app.deps.get_admin_client")
    def test_records_topic_memory(self, mock_admin):
        """Should create a memory for the selected topic."""
        from app.services.agent_memory import record_workflow_memories

        # Mock the admin client's insert response
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-1", "content": "test", "memory_type": "observation"}]
        )
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": {
                "title": "How to close high-ticket clients",
                "novelty_angle": "Use the reversal close technique",
                "opportunity_score": 85,
                "audience_pain": "closing",
            },
            "selected_hook": None,
            "goal_text": "Close more deals",
            "settings": {"platforms": ["youtube"]},
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
            brand_id="brand-1",
        )

        assert len(result) >= 1
        # Verify insert was called
        assert mock_table.insert.called

    @patch("app.deps.get_admin_client")
    def test_records_hook_preference(self, mock_admin):
        """Should create a preference memory for the selected hook."""
        from app.services.agent_memory import record_workflow_memories

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-2", "content": "test", "memory_type": "preference"}]
        )
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": None,
            "selected_hook": {
                "hook_text": "Stop doing this if you want more clients",
                "hook_type": "contrarian",
                "total_score": 92,
            },
            "goal_text": "",
            "settings": {"platforms": ["youtube", "linkedin"]},
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
            brand_id=None,
        )

        assert len(result) >= 1

    @patch("app.deps.get_admin_client")
    def test_records_objective_combo(self, mock_admin):
        """Should create an observation for objective + content_type combo."""
        from app.services.agent_memory import record_workflow_memories

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-3", "content": "test", "memory_type": "observation"}]
        )
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": None,
            "selected_hook": None,
            "goal_text": "Build authority in consulting",
            "settings": {
                "platforms": ["linkedin"],
                "objective": "personal_branding",
                "content_type": "storytelling",
            },
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
        )

        assert len(result) >= 1

    @patch("app.deps.get_admin_client")
    def test_records_feedback_memory(self, mock_admin):
        """Should create a preference memory from approval feedback."""
        from app.services.agent_memory import record_workflow_memories

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-4", "content": "test", "memory_type": "preference"}]
        )
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": None,
            "selected_hook": None,
            "goal_text": "",
            "settings": {"platforms": ["youtube"]},
            "rejection_feedback": "Make the intro shorter and more punchy next time",
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
        )

        assert len(result) >= 1

    @patch("app.deps.get_admin_client")
    def test_records_structure_memory(self, mock_admin):
        """Should create a content_pattern memory from the approved pack."""
        from app.services.agent_memory import record_workflow_memories

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "mem-5", "content": "test", "memory_type": "content_pattern"}]
        )
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": None,
            "selected_hook": None,
            "goal_text": "",
            "settings": {"platforms": ["youtube"]},
            "edited_pack": {
                "youtube_long": {
                    "sections": [
                        {"heading": "Hook"},
                        {"heading": "Problem"},
                        {"heading": "Solution"},
                        {"heading": "CTA"},
                    ]
                },
                "youtube_shorts": [{"script": "short 1"}, {"script": "short 2"}],
                "linkedin_posts": [],
                "twitter_posts": [],
            },
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
        )

        assert len(result) >= 1

    @patch("app.deps.get_admin_client")
    def test_empty_state_returns_empty(self, mock_admin):
        """Should return empty list when state has no actionable data."""
        from app.services.agent_memory import record_workflow_memories

        mock_admin.return_value.table.return_value = MagicMock()

        state = {
            "user_id": "user-test-123",
            "selected_topic": None,
            "selected_hook": None,
            "goal_text": "",
            "settings": {},
        }

        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
        )

        assert result == []

    @patch("app.deps.get_admin_client")
    def test_graceful_failure(self, mock_admin):
        """Should not raise even if individual memory creation fails."""
        from app.services.agent_memory import record_workflow_memories

        mock_table = MagicMock()
        mock_table.insert.side_effect = Exception("DB error")
        mock_admin.return_value.table.return_value = mock_table

        state = {
            "user_id": "user-test-123",
            "selected_topic": {"title": "Test topic", "novelty_angle": "", "opportunity_score": 50},
            "selected_hook": {"hook_text": "Test hook", "hook_type": "story", "total_score": 80},
            "goal_text": "Test goal",
            "settings": {"platforms": ["youtube"], "objective": "sales", "content_type": "educational"},
            "rejection_feedback": "Good work",
            "edited_pack": {"youtube_long": {"sections": [{"heading": "A"}]}},
        }

        # Should not raise
        result = record_workflow_memories(
            user_id="user-test-123",
            workflow_id="wf-abc",
            state=state,
        )

        assert result == []  # All failed gracefully


# ── Advisor rule-based suggestions tests ────────────────────


class TestAdvisorRuleBased:
    """Test rule-based fallback suggestion generation."""

    def test_cadence_alert_when_dormant(self):
        from app.services.advisor import _get_rule_based_suggestions

        signals = {
            "performance": {"has_data": True, "total_posts": 3, "avg_engagement_rate": 0.05, "best_hooks": [], "top_topics": []},
            "memories": {"has_data": False},
            "experiments": {"has_data": False},
            "cadence": {"has_data": True, "days_since_last_content": 10, "recent_workflow_count": 2, "approved_count": 1},
            "schedule": {"has_data": True, "upcoming_count": 0, "next_scheduled": None},
        }

        result = _get_rule_based_suggestions(signals)
        # Should have cadence alert (10 days) and empty schedule alert
        categories = [s["category"] for s in result]
        assert "content" in categories
        assert "schedule" in categories

    def test_best_hook_suggestion(self):
        from app.services.advisor import _get_rule_based_suggestions

        signals = {
            "performance": {
                "has_data": True,
                "total_posts": 10,
                "avg_engagement_rate": 0.08,
                "best_hooks": [
                    {"hook_type": "story", "avg_rate": 0.12, "count": 5},
                    {"hook_type": "question", "avg_rate": 0.06, "count": 3},
                ],
                "top_topics": [],
            },
            "memories": {"has_data": False},
            "experiments": {"has_data": False},
            "cadence": {"has_data": True, "days_since_last_content": 2, "recent_workflow_count": 5, "approved_count": 3},
            "schedule": {"has_data": True, "upcoming_count": 2, "next_scheduled": "2026-02-20"},
        }

        result = _get_rule_based_suggestions(signals)
        # Should have performance suggestion about story hooks
        titles = [s["title"] for s in result]
        has_hook_suggestion = any("story" in t.lower() for t in titles)
        assert has_hook_suggestion

    def test_experiment_pending_suggestion(self):
        from app.services.advisor import _get_rule_based_suggestions

        signals = {
            "performance": {"has_data": False},
            "memories": {"has_data": False},
            "experiments": {
                "has_data": True,
                "active_count": 0,
                "completed_count": 1,
                "proposed_count": 3,
                "active_hypotheses": [],
                "recent_winners": [],
            },
            "cadence": {"has_data": True, "days_since_last_content": 1, "recent_workflow_count": 5, "approved_count": 3},
            "schedule": {"has_data": True, "upcoming_count": 1, "next_scheduled": "2026-02-20"},
        }

        result = _get_rule_based_suggestions(signals)
        categories = [s["category"] for s in result]
        assert "experiment" in categories


class TestAdvisorColdStart:
    """Test cold start suggestions when user has no data."""

    def test_cold_start_returns_starter_tips(self):
        from app.services.advisor import _get_cold_start_suggestions

        result = _get_cold_start_suggestions()
        assert len(result) == 2
        assert result[0]["priority"] == "high"
        assert "create_content" in result[0]["action_type"]


# ── Advisor router tests ────────────────────────────────────


class TestAdvisorEndpoint:
    """Test GET /advisor/suggestions endpoint."""

    @patch("app.routers.advisor.get_suggestions")
    def test_returns_suggestions(self, mock_get, client):
        mock_get.return_value = [
            {
                "title": "Post more consistently",
                "body": "You have not posted in 5 days.",
                "category": "content",
                "priority": "high",
                "action_type": "create_content",
            }
        ]

        resp = client.get("/advisor/suggestions")
        assert resp.status_code == 200

        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Post more consistently"
        mock_get.assert_called_once_with(user_id="user-test-123", brand_id=None, limit=5)

    @patch("app.routers.advisor.get_suggestions")
    def test_passes_brand_id(self, mock_get, client):
        mock_get.return_value = []

        resp = client.get("/advisor/suggestions?brand_id=brand-abc&limit=3")
        assert resp.status_code == 200

        mock_get.assert_called_once_with(user_id="user-test-123", brand_id="brand-abc", limit=3)

    @patch("app.routers.advisor.get_suggestions")
    def test_limits_capped_at_10(self, mock_get, client):
        mock_get.return_value = []

        resp = client.get("/advisor/suggestions?limit=50")
        assert resp.status_code == 200

        mock_get.assert_called_once_with(user_id="user-test-123", brand_id=None, limit=10)
