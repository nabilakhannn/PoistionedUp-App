"""Tests for Slice 73: Daily Briefing Generation.

Covers:
- generate_daily_briefing function
- Briefing sections (schedule, tasks, goals, deliverables)
- Notification creation from briefing
- Edge cases (no data, empty brand)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest


# ── generate_daily_briefing Tests ──────────────────────────────

class TestGenerateDailyBriefing:
    """Test the daily briefing generation logic."""

    def _make_mock_sb(self):
        """Create a mock Supabase client where all query chains return empty data."""
        sb = MagicMock()

        # Create a generic response that returns empty data for any chain
        empty_resp = MagicMock(data=[], count=0)

        # personal_brands: _get_active_brand path
        brand_resp = MagicMock(data=[{"id": "b-1", "name": "Test Brand", "description": "test", "profile_json": {}, "is_active": True}])

        # Use a table-name-aware side_effect
        def table_side_effect(table_name):
            m = MagicMock()
            if table_name == "personal_brands":
                # _get_active_brand: .select().eq().eq().order().limit().execute()
                m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = brand_resp
            elif table_name == "agent_notifications":
                m.insert.return_value.execute.return_value = MagicMock(data=[{"id": "notif-1"}])
            else:
                # For all other tables, return empty data for any chain pattern
                # This handles scheduled_items, agent_tasks, content_posts, agent_goals, agent_deliverables
                for attr in ["select"]:
                    chain = getattr(m, attr).return_value
                    # Chain up to 10 levels deep, each returns empty_resp at execute()
                    for _ in range(10):
                        chain.eq = MagicMock(return_value=chain)
                        chain.in_ = MagicMock(return_value=chain)
                        chain.gte = MagicMock(return_value=chain)
                        chain.lte = MagicMock(return_value=chain)
                        chain.lt = MagicMock(return_value=chain)
                        chain.order = MagicMock(return_value=chain)
                        chain.limit = MagicMock(return_value=chain)
                        chain.contains = MagicMock(return_value=chain)
                        chain.execute = MagicMock(return_value=empty_resp)
            return m

        sb.table.side_effect = table_side_effect
        return sb

    @patch("app.services.agent_orchestrator.get_admin_client")
    def test_briefing_returns_expected_keys(self, mock_client):
        from app.services.agent_orchestrator import generate_daily_briefing

        mock_client.return_value = self._make_mock_sb()
        result = generate_daily_briefing("user-1")
        assert "briefing" in result
        assert "notification_id" in result

    @patch("app.services.agent_orchestrator.get_admin_client")
    def test_briefing_is_string(self, mock_client):
        from app.services.agent_orchestrator import generate_daily_briefing

        mock_client.return_value = self._make_mock_sb()
        result = generate_daily_briefing("user-1")
        assert isinstance(result["briefing"], str)
        assert len(result["briefing"]) > 50  # Not trivially empty

    @patch("app.services.agent_orchestrator.get_admin_client")
    def test_briefing_contains_brand_name(self, mock_client):
        from app.services.agent_orchestrator import generate_daily_briefing

        mock_client.return_value = self._make_mock_sb()
        result = generate_daily_briefing("user-1")
        assert "Test Brand" in result["briefing"]

    @patch("app.services.agent_orchestrator.get_admin_client")
    def test_briefing_creates_notification(self, mock_client):
        from app.services.agent_orchestrator import generate_daily_briefing

        mock_sb = self._make_mock_sb()
        mock_client.return_value = mock_sb
        result = generate_daily_briefing("user-1")
        assert result.get("notification_id") is not None


# ── Handler Integration ──────────────────────────────────────────

class TestDailyBriefingHandler:
    """Test _handle_daily_briefing dispatches to generate_daily_briefing."""

    @patch("app.services.agent_orchestrator.generate_daily_briefing")
    def test_handler_calls_generate(self, mock_generate):
        from app.services.agent_orchestrator import _handle_daily_briefing

        mock_generate.return_value = {
            "briefing": "# Morning Briefing\nAll good.",
            "notification_id": "notif-1",
        }

        result = _handle_daily_briefing(
            task={"id": "t-1", "title": "Daily Briefing"},
            user_id="user-1",
            brand={"id": "b-1", "name": "Test Brand"},
            sb=MagicMock(),
        )

        mock_generate.assert_called_once_with("user-1")
        assert result["deliverable_type"] == "report"
        assert "briefing" in result["content"].lower() or len(result["content"]) > 0


# ── Content Gap Fill Handler ────────────────────────────────────

class TestContentGapFillHandler:
    """Test _handle_content_gap_fill handler."""

    def test_handler_returns_report(self):
        from app.services.agent_orchestrator import _handle_content_gap_fill

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = _handle_content_gap_fill(
            task={"id": "t-1", "title": "Content Check"},
            user_id="user-1",
            brand={"id": "b-1", "name": "Test Brand"},
            sb=sb,
        )

        assert result["deliverable_type"] == "report"
        assert "Content Calendar" in result["title"]
        assert "Test Brand" in result["title"]


# ── Performance Alert Handler ───────────────────────────────────

class TestPerformanceAlertHandler:
    """Test _handle_performance_alert handler."""

    def test_handler_returns_report_no_posts(self):
        from app.services.agent_orchestrator import _handle_performance_alert

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = _handle_performance_alert(
            task={"id": "t-1", "title": "Performance Scan"},
            user_id="user-1",
            brand={"id": "b-1", "name": "Test Brand"},
            sb=sb,
        )

        assert result["deliverable_type"] == "report"
        assert "No posts found" in result["content"] or "Performance" in result["title"]

    def test_handler_with_posts(self):
        from app.services.agent_orchestrator import _handle_performance_alert

        sb = MagicMock()

        # Weekly posts
        weekly_data = [
            {"engagement_rate": 5.0},
            {"engagement_rate": 4.0},
            {"engagement_rate": 6.0},
        ]
        today_data = [
            {"id": "p-1", "title": "Good Post", "engagement_rate": 12.0, "platform": "linkedin", "performance_tier": "viral"},
            {"id": "p-2", "title": "Bad Post", "engagement_rate": 0.5, "platform": "linkedin", "performance_tier": "flop"},
        ]

        call_count = [0]

        def gte_side_effect(*args, **kwargs):
            call_count[0] += 1
            m = MagicMock()
            if call_count[0] == 1:
                m.execute.return_value = MagicMock(data=weekly_data)
            else:
                m.execute.return_value = MagicMock(data=today_data)
            return m

        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.side_effect = gte_side_effect

        result = _handle_performance_alert(
            task={"id": "t-1", "title": "Performance Scan"},
            user_id="user-1",
            brand={"id": "b-1", "name": "Test Brand"},
            sb=sb,
        )

        assert result["deliverable_type"] == "report"
        assert "Performance Scan" in result["title"]
