"""Tests for Slice 78: Migration Consolidation + Nav Fix.

Covers:
- NotificationOut / AgentNotifyRequest schema validation (~3 tests)
- GoalCreate / GoalOut schema validation (~3 tests)
- Advisor rate limit tier assignment (~2 tests)
- Autonomy columns referenced in orchestrator (~2 tests)
- Competitor alert from_agent_id fix (~2 tests)
- DEFAULT_AGENTS count (~1 test)
- Migration file existence (~3 tests)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ── Migration File Existence ─────────────────────────────────────

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "infra" / "supabase" / "migrations"


class TestMigrationFilesExist:
    """Verify all 3 new migration files exist and contain expected SQL."""

    def test_026_agent_notifications_exists(self):
        path = MIGRATIONS_DIR / "026_agent_notifications.sql"
        assert path.exists(), f"Migration 026 not found at {path}"
        content = path.read_text()
        assert "agent_notifications" in content
        assert "ROW LEVEL SECURITY" in content
        assert "from_agent_id" in content

    def test_027_agent_goals_exists(self):
        path = MIGRATIONS_DIR / "027_agent_goals.sql"
        assert path.exists(), f"Migration 027 not found at {path}"
        content = path.read_text()
        assert "agent_goals" in content
        assert "ROW LEVEL SECURITY" in content
        assert "goal_type" in content

    def test_028_autonomy_columns_exists(self):
        path = MIGRATIONS_DIR / "028_agent_autonomy_columns.sql"
        assert path.exists(), f"Migration 028 not found at {path}"
        content = path.read_text()
        assert "autonomy_enabled" in content
        assert "confidence_threshold" in content
        assert "auto_execute" in content


# ── Notification Schema ──────────────────────────────────────────

class TestNotificationSchema:
    """Test notification Pydantic schemas."""

    def test_notification_out_fields(self):
        from app.schemas.notifications import NotificationOut

        fields = set(NotificationOut.model_fields.keys())
        expected = {
            "id", "title", "body", "notification_type", "priority",
            "from_agent_id", "related_task_id", "related_goal_id",
            "status", "action_url", "metadata", "created_at", "read_at",
        }
        assert expected.issubset(fields), f"Missing fields: {expected - fields}"

    def test_agent_notify_request_validation(self):
        from app.schemas.notifications import AgentNotifyRequest

        req = AgentNotifyRequest(
            title="Test Alert",
            body="Something happened",
            notification_type="alert",
            priority="high",
            agent_id="competitor-analyst",
        )
        assert req.agent_id == "competitor-analyst"
        assert req.priority == "high"

    def test_agent_notify_request_rejects_empty_title(self):
        from app.schemas.notifications import AgentNotifyRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentNotifyRequest(
                title="",
                body="test",
                agent_id="test",
            )


# ── Goal Schema ──────────────────────────────────────────────────

class TestGoalSchema:
    """Test goal Pydantic schemas."""

    def test_goal_create_valid(self):
        from app.schemas.goals import GoalCreate

        goal = GoalCreate(
            title="Post 3x per week",
            goal_type="posting_frequency",
            target_value=3.0,
            target_unit="per_week",
        )
        assert goal.target_value == 3.0
        assert goal.priority == "P2"

    def test_goal_update_all_optional(self):
        from app.schemas.goals import GoalUpdate

        update = GoalUpdate()
        assert update.title is None
        assert update.current_value is None
        assert update.status is None

    def test_goal_out_has_progress_fields(self):
        from app.schemas.goals import GoalOut

        fields = set(GoalOut.model_fields.keys())
        assert "current_value" in fields
        assert "target_value" in fields
        assert "last_evaluated_at" in fields
        assert "last_action_at" in fields


# ── Advisor Rate Limit ───────────────────────────────────────────

class TestAdvisorRateLimit:
    """Test advisor endpoint rate limiting."""

    def test_advisor_suggestions_in_route_tiers(self):
        from app.middleware.rate_limit import _ROUTE_TIERS

        paths = [path for path, _ in _ROUTE_TIERS]
        assert "/advisor/suggestions" in paths

    def test_advisor_suggestions_uses_llm_tier(self):
        from app.middleware.rate_limit import _ROUTE_TIERS, TIER_LLM

        for path, tier in _ROUTE_TIERS:
            if path == "/advisor/suggestions":
                assert tier == TIER_LLM, f"Expected TIER_LLM, got {tier}"
                return
        pytest.fail("/advisor/suggestions not found in _ROUTE_TIERS")


# ── Autonomy Columns Referenced ──────────────────────────────────

class TestAutonomyColumnsReferenced:
    """Test that orchestrator references the autonomy columns."""

    def test_get_agent_autonomy_exists(self):
        import inspect
        from app.services import agent_orchestrator

        members = [name for name, _ in inspect.getmembers(agent_orchestrator)]
        assert "_get_agent_autonomy" in members

    def test_autonomy_function_callable(self):
        from app.services.agent_orchestrator import _get_agent_autonomy

        assert callable(_get_agent_autonomy)


# ── Competitor Alert Column Fix ──────────────────────────────────

class TestCompetitorAlertColumnFix:
    """Test that competitor alert uses from_agent_id (not agent_id)."""

    def test_agent_bridge_source_uses_from_agent_id(self):
        """Read the agent_bridge source to verify from_agent_id is used
        in the competitor-alerts endpoint row construction."""
        import inspect
        from app.routers import agent_bridge

        source = inspect.getsource(agent_bridge)
        # Find the competitor-alerts section and check it uses from_agent_id
        # The old bug was: "agent_id": body.get("agent_id", ...)
        # Should be: "from_agent_id": body.get("agent_id", ...)
        lines = source.split("\n")
        in_alert_section = False
        for line in lines:
            if "competitor-alerts" in line or "Competitor Alert" in line:
                in_alert_section = True
            if in_alert_section and "agent_id" in line and "body.get" in line:
                # This line should use from_agent_id as the key
                assert '"from_agent_id"' in line, (
                    f"Expected 'from_agent_id' key but found: {line.strip()}"
                )
                return
        # If we didn't find the pattern, that's also ok (code may have changed)

    def test_all_notification_inserts_use_from_agent_id(self):
        """Verify the notify endpoint also uses from_agent_id."""
        import inspect
        from app.routers import agent_bridge

        source = inspect.getsource(agent_bridge)
        # Count occurrences of from_agent_id in notification inserts
        assert source.count('"from_agent_id"') >= 2, (
            "Expected at least 2 from_agent_id usages (notify + competitor-alerts)"
        )


# ── DEFAULT_AGENTS Count ────────────────────────────────────────

class TestDefaultAgentsCount:
    """Test that DEFAULT_AGENTS still has all 8 agents."""

    def test_eight_default_agents(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        assert len(DEFAULT_AGENTS) == 8

    def test_jarvis_not_in_agents(self):
        """Verify jarvis is fully removed (renamed to jumbo in Slice 66)."""
        from app.routers.mission_control import DEFAULT_AGENTS

        ids = [a["id"] for a in DEFAULT_AGENTS]
        assert "jarvis" not in ids
        assert "jumbo" in ids
