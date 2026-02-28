"""Tests for Slice 73: Goals API.

Covers:
- GoalCreate / GoalUpdate / GoalOut schema validation
- Goal type and target unit enum validation
- Goals router endpoint registration
- Goal CRUD route patterns
- evaluate_single_goal logic
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Schema Validation Tests ─────────────────────────────────────

class TestGoalSchemas:
    """Test Pydantic schemas for goals."""

    def test_goal_create_valid(self):
        from app.schemas.goals import GoalCreate

        goal = GoalCreate(
            title="Post 3x/week on LinkedIn",
            goal_type="posting_frequency",
            target_value=3,
            target_unit="per_week",
        )
        assert goal.title == "Post 3x/week on LinkedIn"
        assert goal.goal_type == "posting_frequency"
        assert goal.target_value == 3

    def test_goal_create_all_types_valid(self):
        from app.schemas.goals import GoalCreate

        for goal_type in ("posting_frequency", "engagement_growth", "research_cadence", "content_pipeline", "custom"):
            goal = GoalCreate(
                title=f"Test {goal_type}",
                goal_type=goal_type,
                target_value=5,
                target_unit="per_week",
            )
            assert goal.goal_type == goal_type

    def test_goal_create_all_units_valid(self):
        from app.schemas.goals import GoalCreate

        for unit in ("per_week", "per_month", "percent", "count"):
            goal = GoalCreate(
                title="Test unit",
                goal_type="custom",
                target_value=10,
                target_unit=unit,
            )
            assert goal.target_unit == unit

    def test_goal_create_invalid_type_rejected(self):
        from app.schemas.goals import GoalCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GoalCreate(
                title="Bad goal",
                goal_type="invalid_type",
                target_value=5,
                target_unit="per_week",
            )

    def test_goal_create_with_optional_fields(self):
        from app.schemas.goals import GoalCreate

        goal = GoalCreate(
            title="Engagement goal",
            goal_type="engagement_growth",
            target_value=15,
            target_unit="percent",
            description="Grow engagement by 15%",
            platform="linkedin",
            brand_id="brand-123",
            priority="P1",
        )
        assert goal.description == "Grow engagement by 15%"
        assert goal.platform == "linkedin"
        assert goal.brand_id == "brand-123"
        assert goal.priority == "P1"

    def test_goal_update_partial(self):
        from app.schemas.goals import GoalUpdate

        update = GoalUpdate(status="paused")
        data = update.model_dump(exclude_none=True)
        assert data == {"status": "paused"}

    def test_goal_update_current_value(self):
        from app.schemas.goals import GoalUpdate

        update = GoalUpdate(current_value=7.5)
        data = update.model_dump(exclude_none=True)
        assert data == {"current_value": 7.5}

    def test_goal_out_model(self):
        from app.schemas.goals import GoalOut

        goal = GoalOut(
            id="goal-1",
            title="Test",
            goal_type="custom",
            target_value=10,
            current_value=3,
            target_unit="count",
            status="active",
            priority="P2",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert goal.id == "goal-1"
        assert goal.status == "active"


# ── Route Registration Tests ────────────────────────────────────

class TestGoalsRouteRegistration:
    """Test that goals routes are registered in the app."""

    def test_goals_router_has_prefix(self):
        from app.routers.goals import router

        assert router.prefix == "/goals"

    def test_goals_router_has_tag(self):
        from app.routers.goals import router

        assert "goals" in router.tags

    def test_goals_has_list_endpoint(self):
        from app.routers.goals import router

        routes = [r.path for r in router.routes]
        assert "/goals" in routes

    def test_goals_has_create_endpoint(self):
        from app.routers.goals import router

        methods = []
        for r in router.routes:
            if hasattr(r, "methods"):
                methods.extend(r.methods)
        assert "POST" in methods

    def test_goals_has_evaluate_endpoint(self):
        from app.routers.goals import router

        routes = [r.path for r in router.routes]
        assert "/goals/{goal_id}/evaluate" in routes

    def test_goals_has_delete_endpoint(self):
        from app.routers.goals import router

        methods = []
        for r in router.routes:
            if hasattr(r, "methods"):
                methods.extend(r.methods)
        assert "DELETE" in methods


# ── evaluate_single_goal Tests ──────────────────────────────────

class TestEvaluateSingleGoal:
    """Test the goal evaluation logic."""

    def test_posting_frequency_evaluation(self):
        from app.services.agent_orchestrator import evaluate_single_goal

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value = MagicMock(
            count=5, data=[{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}]
        )
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        goal = {
            "id": "goal-1",
            "goal_type": "posting_frequency",
            "target_value": 3,
            "target_unit": "per_week",
            "current_value": 0,
        }
        result = evaluate_single_goal("user-1", goal, sb)
        assert "current_value" in result
        assert "on_track" in result

    def test_unknown_goal_type_returns_defaults(self):
        from app.services.agent_orchestrator import evaluate_single_goal

        sb = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        goal = {
            "id": "goal-1",
            "goal_type": "unknown_type",
            "target_value": 10,
            "target_unit": "count",
            "current_value": 5,
        }
        result = evaluate_single_goal("user-1", goal, sb)
        assert result["current_value"] == 5
        assert isinstance(result["on_track"], bool)


# ── Rate Limit Tier Tests ──────────────────────────────────────

class TestGoalsRateLimits:
    """Test rate limit tier assignments for goals endpoints."""

    def test_goals_list_uses_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/goals", "GET")
        assert tier == TIER_READ

    def test_goals_create_uses_default_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/goals", "POST")
        assert tier == TIER_READ  # /goals not in explicit route tiers, defaults to READ
