"""Tests for Slice 73: Proactive Pulse Engine.

Covers:
- Daily schedule definitions and structure
- _is_daily_due evaluation logic
- Proactive condition checks (content gaps, performance drops, stale research, deliverables, goals)
- Autonomy gating during pulse
- _create_notification helper
- _evaluate_proactive_conditions aggregation
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest


# ── Daily Schedule Definitions ──────────────────────────────────

class TestDailyScheduleDefinitions:
    """Test that DAILY_SCHEDULES are well-formed."""

    def test_four_daily_schedules_defined(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        assert len(DAILY_SCHEDULES) == 6

    def test_all_daily_schedules_have_required_fields(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        required = {"id", "name", "hour", "tz_offset", "agent_id",
                     "task_type", "priority", "brief", "cooldown_hours"}
        for schedule in DAILY_SCHEDULES:
            missing = required - set(schedule.keys())
            assert not missing, f"Daily schedule {schedule.get('id')} missing fields: {missing}"

    def test_daily_schedule_ids_unique(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        ids = [s["id"] for s in DAILY_SCHEDULES]
        assert len(ids) == len(set(ids)), "Duplicate daily schedule IDs found"

    def test_daily_schedule_ids_match_expected(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        expected = {"daily_briefing", "daily_content_check", "midday_performance", "evening_performance", "daily_competitor_scan", "daily_qa_review"}
        actual = {s["id"] for s in DAILY_SCHEDULES}
        assert actual == expected

    def test_daily_schedule_task_types_have_handlers(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES, _get_handlers

        handlers = _get_handlers()
        for schedule in DAILY_SCHEDULES:
            assert schedule["task_type"] in handlers, (
                f"Daily schedule {schedule['id']} has unknown task_type: {schedule['task_type']}"
            )


# ── _is_daily_due tests ──────────────────────────────────────────

class TestIsDailyDue:
    """Test the daily schedule due-date evaluation logic."""

    def test_due_after_hour(self):
        from app.services.agent_orchestrator import _is_daily_due

        schedule = {"hour": 8, "tz_offset": 0}
        now = datetime(2026, 2, 27, 10, 0, tzinfo=timezone.utc)
        assert _is_daily_due(schedule, now) is True

    def test_due_at_exact_hour(self):
        from app.services.agent_orchestrator import _is_daily_due

        schedule = {"hour": 8, "tz_offset": 0}
        now = datetime(2026, 2, 27, 8, 0, tzinfo=timezone.utc)
        assert _is_daily_due(schedule, now) is True

    def test_not_due_before_hour(self):
        from app.services.agent_orchestrator import _is_daily_due

        schedule = {"hour": 8, "tz_offset": 0}
        now = datetime(2026, 2, 27, 7, 30, tzinfo=timezone.utc)
        assert _is_daily_due(schedule, now) is False

    def test_due_with_tz_offset(self):
        from app.services.agent_orchestrator import _is_daily_due

        schedule = {"hour": 8, "tz_offset": -5}  # 8 AM EST
        now = datetime(2026, 2, 27, 13, 0, tzinfo=timezone.utc)  # 13 UTC = 8 EST
        assert _is_daily_due(schedule, now) is True

    def test_not_due_with_tz_offset_too_early(self):
        from app.services.agent_orchestrator import _is_daily_due

        schedule = {"hour": 8, "tz_offset": -5}
        now = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)  # 12 UTC = 7 EST
        assert _is_daily_due(schedule, now) is False


# ── Proactive Condition Check Tests ─────────────────────────────

class TestCheckContentGaps:
    """Test the _check_content_gaps proactive check."""

    def _mock_sb_content_gap(self, count: int):
        sb = MagicMock()
        mock_resp = MagicMock(count=count, data=[])
        sb.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.lte.return_value.execute.return_value = mock_resp
        return sb

    def test_returns_finding_when_empty_calendar(self):
        from app.services.agent_orchestrator import _check_content_gaps

        sb = self._mock_sb_content_gap(0)
        result = _check_content_gaps("user-1", {"id": "b-1", "name": "Test"}, sb)

        assert result is not None
        assert "0 item" in result["summary"]
        assert result["notification"]["priority"] == "high"

    def test_returns_finding_when_low_count(self):
        from app.services.agent_orchestrator import _check_content_gaps

        sb = self._mock_sb_content_gap(1)
        result = _check_content_gaps("user-1", {"id": "b-1", "name": "Test"}, sb)

        assert result is not None
        assert result["notification"]["priority"] == "medium"

    def test_returns_none_when_calendar_full(self):
        from app.services.agent_orchestrator import _check_content_gaps

        sb = self._mock_sb_content_gap(5)
        result = _check_content_gaps("user-1", {"id": "b-1", "name": "Test"}, sb)

        assert result is None


class TestCheckPerformanceDrops:
    """Test the _check_performance_drops proactive check."""

    def _mock_sb_performance(self, this_week_rates, last_week_rates):
        sb = MagicMock()

        tw_resp = MagicMock(data=[{"engagement_rate": r} for r in this_week_rates])
        lw_resp = MagicMock(data=[{"engagement_rate": r} for r in last_week_rates])

        # Chaining for this_week and last_week queries
        call_count = [0]
        original_gte = sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte

        def gte_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock = MagicMock()
            if call_count[0] == 1:
                mock.execute.return_value = tw_resp
            else:
                mock.lt.return_value.execute.return_value = lw_resp
            return mock

        original_gte.side_effect = gte_side_effect

        return sb

    def test_returns_none_when_insufficient_data(self):
        from app.services.agent_orchestrator import _check_performance_drops

        sb = MagicMock()
        tw_resp = MagicMock(data=[{"engagement_rate": 5.0}])
        lw_resp = MagicMock(data=[])
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = tw_resp
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lt.return_value.execute.return_value = lw_resp

        result = _check_performance_drops("user-1", {"id": "b-1", "name": "Test"}, sb)
        # With insufficient data it should return None
        assert result is None


class TestCheckStaleResearch:
    """Test the _check_stale_research proactive check."""

    def test_returns_finding_when_no_sessions(self):
        from app.services.agent_orchestrator import _check_stale_research

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        result = _check_stale_research("user-1", {"id": "b-1", "name": "Test"}, sb)
        assert result is not None
        assert "stale" in result["summary"].lower() or "research" in result["summary"].lower()


class TestCheckUnreviewedDeliverables:
    """Test the _check_unreviewed_deliverables proactive check."""

    def test_returns_finding_when_old_deliverables(self):
        from app.services.agent_orchestrator import _check_unreviewed_deliverables

        sb = MagicMock()
        old_date = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=3, data=[{"id": "d-1"}, {"id": "d-2"}, {"id": "d-3"}]
        )

        result = _check_unreviewed_deliverables("user-1", {"id": "b-1", "name": "Test"}, sb)
        assert result is not None
        assert "3" in result["summary"]


# ── _get_agent_autonomy tests ──────────────────────────────────

class TestGetAgentAutonomy:
    """Test the autonomy settings retrieval."""

    def test_returns_settings_when_found(self):
        from app.services.agent_orchestrator import _get_agent_autonomy

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"autonomy_enabled": True, "confidence_threshold": 0.8, "auto_execute": True}]
        )

        result = _get_agent_autonomy("jumbo", "user-1", sb)
        assert result is not None
        assert result["autonomy_enabled"] is True

    def test_returns_none_when_not_found(self):
        from app.services.agent_orchestrator import _get_agent_autonomy

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = _get_agent_autonomy("jumbo", "user-1", sb)
        assert result is None

    def test_returns_none_on_error(self):
        from app.services.agent_orchestrator import _get_agent_autonomy

        sb = MagicMock()
        sb.table.side_effect = Exception("DB error")

        result = _get_agent_autonomy("jumbo", "user-1", sb)
        assert result is None


# ── _create_notification tests ──────────────────────────────────

class TestCreateNotification:
    """Test the notification creation helper."""

    def test_creates_notification_row(self):
        from app.services.agent_orchestrator import _create_notification

        sb = MagicMock()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "notif-123"}]
        )

        result = _create_notification("user-1", {
            "title": "Test Alert",
            "body": "Something happened",
            "type": "alert",
            "priority": "high",
            "agent_id": "analytics",
        }, sb)

        assert result == "notif-123"
        sb.table.assert_called_with("agent_notifications")

    def test_returns_none_on_error(self):
        from app.services.agent_orchestrator import _create_notification

        sb = MagicMock()
        sb.table.return_value.insert.side_effect = Exception("Insert failed")

        result = _create_notification("user-1", {
            "title": "Test",
            "body": "Test",
        }, sb)

        assert result is None


# ── Extended Pulse Tests ────────────────────────────────────────

class TestPulseWithDailySchedules:
    """Test pulse() includes daily schedules."""

    @patch("app.services.agent_orchestrator.get_admin_client")
    @patch("app.services.agent_orchestrator._is_schedule_due", return_value=False)
    @patch("app.services.agent_orchestrator._is_daily_due", return_value=False)
    @patch("app.services.agent_orchestrator._get_active_brand", return_value=None)
    def test_pulse_skips_all_when_no_brand(self, mock_brand, mock_daily, mock_due, mock_client):
        from app.services.agent_orchestrator import pulse, SCHEDULES, DAILY_SCHEDULES

        mock_client.return_value = MagicMock()
        result = pulse("user-123")

        # All weekly and daily should be skipped
        total_schedules = len(SCHEDULES) + len(DAILY_SCHEDULES)
        assert len(result["skipped"]) == total_schedules
        assert len(result["created_tasks"]) == 0
        assert "proactive_findings" in result
        assert "notifications_created" in result

    def test_pulse_returns_notifications_created_count(self):
        """Verify pulse result includes notifications_created field."""
        from app.services.agent_orchestrator import pulse

        with patch("app.services.agent_orchestrator.get_admin_client") as mock_client, \
             patch("app.services.agent_orchestrator._is_schedule_due", return_value=False), \
             patch("app.services.agent_orchestrator._is_daily_due", return_value=False), \
             patch("app.services.agent_orchestrator._get_active_brand", return_value=None):

            mock_client.return_value = MagicMock()
            result = pulse("user-123")

            assert isinstance(result["notifications_created"], int)
            assert result["notifications_created"] == 0


# ── Trigger Schedule Extension ─────────────────────────────────

class TestTriggerScheduleExtension:
    """Test that trigger_schedule now supports daily schedule IDs."""

    def test_trigger_resolves_daily_schedule(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        # Verify daily_briefing is a valid schedule ID
        daily_ids = {s["id"] for s in DAILY_SCHEDULES}
        assert "daily_briefing" in daily_ids
        assert "daily_content_check" in daily_ids
        assert "midday_performance" in daily_ids
        assert "evening_performance" in daily_ids


# ── Schema validation for daily schedules ──────────────────────

class TestExtendedSchemaValidation:
    """Test that TriggerRequest accepts new daily schedule IDs."""

    def test_trigger_request_accepts_daily_briefing(self):
        from app.schemas.orchestrator import TriggerRequest

        req = TriggerRequest(schedule_id="daily_briefing")
        assert req.schedule_id == "daily_briefing"

    def test_trigger_request_accepts_daily_content_check(self):
        from app.schemas.orchestrator import TriggerRequest

        req = TriggerRequest(schedule_id="daily_content_check")
        assert req.schedule_id == "daily_content_check"

    def test_trigger_request_accepts_midday_performance(self):
        from app.schemas.orchestrator import TriggerRequest

        req = TriggerRequest(schedule_id="midday_performance")
        assert req.schedule_id == "midday_performance"

    def test_trigger_request_accepts_evening_performance(self):
        from app.schemas.orchestrator import TriggerRequest

        req = TriggerRequest(schedule_id="evening_performance")
        assert req.schedule_id == "evening_performance"
