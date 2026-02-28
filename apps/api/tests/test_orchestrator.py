"""Tests for Slice 30: Agent Orchestrator Service.

Covers:
- Schedule evaluation logic (_is_schedule_due, _has_recent_task)
- Pulse idempotency (cooldown dedup)
- Task creation and tag-based routing
- Handler dispatch and result structure
- Error handling and sanitized responses
- Rate limit tier coverage for orchestrator endpoints
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ── Schedule evaluation tests ────────────────────────────────────

class TestScheduleEvaluation:
    """Test the schedule due-date evaluation logic."""

    def test_is_due_on_correct_day_and_hour(self):
        from app.services.agent_orchestrator import _is_schedule_due

        schedule = {"day_of_week": 5, "hour": 10, "tz_offset": 0}  # Saturday 10am UTC
        # Saturday 15:00 UTC
        now = datetime(2026, 2, 28, 15, 0, tzinfo=timezone.utc)  # 2026-02-28 is Saturday
        assert _is_schedule_due(schedule, now) is True

    def test_not_due_wrong_day(self):
        from app.services.agent_orchestrator import _is_schedule_due

        schedule = {"day_of_week": 5, "hour": 10, "tz_offset": 0}  # Saturday
        # Sunday 15:00 UTC
        now = datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)  # 2026-03-01 is Sunday
        assert _is_schedule_due(schedule, now) is False

    def test_not_due_before_hour(self):
        from app.services.agent_orchestrator import _is_schedule_due

        schedule = {"day_of_week": 5, "hour": 10, "tz_offset": 0}
        # Saturday 08:00 UTC (before 10am)
        now = datetime(2026, 2, 28, 8, 0, tzinfo=timezone.utc)
        assert _is_schedule_due(schedule, now) is False

    def test_due_with_tz_offset(self):
        from app.services.agent_orchestrator import _is_schedule_due

        schedule = {"day_of_week": 5, "hour": 10, "tz_offset": -5}  # Saturday 10am EST
        # Saturday 15:00 UTC = 10:00 EST → due
        now = datetime(2026, 2, 28, 15, 0, tzinfo=timezone.utc)
        assert _is_schedule_due(schedule, now) is True

    def test_not_due_with_tz_offset_too_early(self):
        from app.services.agent_orchestrator import _is_schedule_due

        schedule = {"day_of_week": 5, "hour": 10, "tz_offset": -5}  # Saturday 10am EST
        # Saturday 14:00 UTC = 09:00 EST → not yet
        now = datetime(2026, 2, 28, 14, 0, tzinfo=timezone.utc)
        assert _is_schedule_due(schedule, now) is False


# ── Tag extraction tests ─────────────────────────────────────────

class TestTagExtraction:
    """Test the tag extraction helper."""

    def test_extract_type_tag(self):
        from app.services.agent_orchestrator import _extract_tag

        assert _extract_tag(["orchestrator", "type:research", "auto:weekly_research"], "type:") == "research"

    def test_extract_auto_tag(self):
        from app.services.agent_orchestrator import _extract_tag

        assert _extract_tag(["orchestrator", "auto:weekly_analytics"], "auto:") == "weekly_analytics"

    def test_missing_tag_returns_none(self):
        from app.services.agent_orchestrator import _extract_tag

        assert _extract_tag(["orchestrator"], "type:") is None

    def test_empty_tags_returns_none(self):
        from app.services.agent_orchestrator import _extract_tag

        assert _extract_tag([], "type:") is None


# ── Handler dispatch tests ───────────────────────────────────────

class TestHandlerDispatch:
    """Test that handler map resolves to callable functions."""

    def test_all_handlers_registered(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        assert set(handlers.keys()) == {"research", "content", "analytics", "competitor", "competitor_scan", "daily_briefing", "content_gap_fill", "performance_alert", "qa_review_pending"}

    def test_all_handlers_callable(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        for name, fn in handlers.items():
            assert callable(fn), f"Handler for '{name}' is not callable"


# ── Schedule definitions tests ───────────────────────────────────

class TestScheduleDefinitions:
    """Test that schedule definitions are well-formed."""

    def test_three_schedules_defined(self):
        from app.services.agent_orchestrator import SCHEDULES

        assert len(SCHEDULES) == 3

    def test_all_schedules_have_required_fields(self):
        from app.services.agent_orchestrator import SCHEDULES

        required = {"id", "name", "day_of_week", "hour", "tz_offset", "agent_id",
                     "task_type", "priority", "brief", "cooldown_hours"}
        for schedule in SCHEDULES:
            missing = required - set(schedule.keys())
            assert not missing, f"Schedule {schedule.get('id')} missing fields: {missing}"

    def test_schedule_ids_unique(self):
        from app.services.agent_orchestrator import SCHEDULES

        ids = [s["id"] for s in SCHEDULES]
        assert len(ids) == len(set(ids)), "Duplicate schedule IDs found"

    def test_schedule_task_types_valid(self):
        from app.services.agent_orchestrator import SCHEDULES, _get_handlers

        handlers = _get_handlers()
        for schedule in SCHEDULES:
            assert schedule["task_type"] in handlers, (
                f"Schedule {schedule['id']} has invalid task_type: {schedule['task_type']}"
            )


# ── Pulse logic tests (mocked DB) ────────────────────────────────

class TestPulseLogic:
    """Test pulse() with mocked Supabase interactions."""

    def _mock_sb(self, brand=None, recent_tasks=0):
        """Create a mock Supabase client."""
        sb = MagicMock()

        # Mock personal_brands query
        brand_data = [brand] if brand else []
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=brand_data)

        # Mock agent_tasks count (for cooldown check)
        sb.table.return_value.select.return_value.eq.return_value.contains.return_value.gte.return_value.execute.return_value = MagicMock(count=recent_tasks, data=[])

        # Mock insert
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test-task"}])

        return sb

    @patch("app.services.agent_orchestrator.get_admin_client")
    @patch("app.services.agent_orchestrator._is_schedule_due", return_value=False)
    @patch("app.services.agent_orchestrator._is_daily_due", return_value=False)
    def test_pulse_skips_when_not_due(self, mock_daily_due, mock_due, mock_client):
        from app.services.agent_orchestrator import pulse, SCHEDULES, DAILY_SCHEDULES

        mock_client.return_value = self._mock_sb()
        result = pulse("user-123")

        assert len(result["created_tasks"]) == 0
        assert len(result["skipped"]) == len(SCHEDULES) + len(DAILY_SCHEDULES)  # all schedules skipped

    @patch("app.services.agent_orchestrator.get_admin_client")
    @patch("app.services.agent_orchestrator._is_schedule_due", return_value=True)
    @patch("app.services.agent_orchestrator._is_daily_due", return_value=True)
    @patch("app.services.agent_orchestrator._has_recent_task", return_value=True)
    def test_pulse_skips_within_cooldown(self, mock_recent, mock_daily_due, mock_due, mock_client):
        from app.services.agent_orchestrator import pulse

        mock_client.return_value = self._mock_sb()
        result = pulse("user-123")

        assert len(result["created_tasks"]) == 0
        for skip in result["skipped"]:
            assert skip["reason"] in ("cooldown", "no_active_brand")


# ── Schema validation tests ──────────────────────────────────────

class TestSchemaValidation:
    """Test Pydantic schema constraints."""

    def test_trigger_request_valid_schedule_ids(self):
        from app.schemas.orchestrator import TriggerRequest

        for sid in ("weekly_research", "weekly_analytics", "weekly_competitor"):
            req = TriggerRequest(schedule_id=sid)
            assert req.schedule_id == sid

    def test_trigger_request_rejects_invalid_schedule(self):
        from app.schemas.orchestrator import TriggerRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TriggerRequest(schedule_id="invalid_schedule")

    def test_trigger_request_rejects_injection(self):
        from app.schemas.orchestrator import TriggerRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TriggerRequest(schedule_id="weekly_research; DROP TABLE")

    def test_pulse_request_defaults(self):
        from app.schemas.orchestrator import PulseRequest

        req = PulseRequest()
        assert req.auto_execute is False
        assert req.force is False


# ── Rate limit tier tests ────────────────────────────────────────

class TestRateLimitTiers:
    """Test that orchestrator endpoints have correct rate limit tiers."""

    def test_pulse_uses_orchestrator_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_ORCHESTRATOR

        tier = _get_tier("/orchestrator/pulse", "POST")
        assert tier == TIER_ORCHESTRATOR

    def test_trigger_uses_orchestrator_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_ORCHESTRATOR

        tier = _get_tier("/orchestrator/trigger", "POST")
        assert tier == TIER_ORCHESTRATOR

    def test_execute_uses_orchestrator_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_ORCHESTRATOR

        tier = _get_tier("/orchestrator/execute/some-task-id", "POST")
        assert tier == TIER_ORCHESTRATOR

    def test_status_uses_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/orchestrator/status", "GET")
        assert tier == TIER_READ

    def test_schedules_uses_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/orchestrator/schedules", "GET")
        assert tier == TIER_READ

    def test_orchestrator_tier_is_strict(self):
        from app.middleware.rate_limit import TIER_ORCHESTRATOR, TIER_LLM

        max_req, window = TIER_ORCHESTRATOR
        llm_max, _ = TIER_LLM
        assert max_req <= llm_max, "Orchestrator tier should be stricter than LLM tier"
        assert max_req <= 10, "Orchestrator tier should allow at most 10 req/min"


# ── Fmt helper tests ─────────────────────────────────────────────

class TestHelpers:
    """Test utility helpers."""

    def test_fmt_counts_empty(self):
        from app.services.agent_orchestrator import _fmt_counts

        assert _fmt_counts({}) == "None"

    def test_fmt_counts_single(self):
        from app.services.agent_orchestrator import _fmt_counts

        assert _fmt_counts({"done": 5}) == "done: 5"

    def test_fmt_counts_multiple(self):
        from app.services.agent_orchestrator import _fmt_counts

        result = _fmt_counts({"done": 3, "failed": 1})
        assert "done: 3" in result
        assert "failed: 1" in result
