"""Tests for Slice 77: Dedicated Competitor Analysis Agent.

Covers:
- ThreatScoreDetail / CompetitorAlert / IntelligenceFeed schema validation (~8 tests)
- CompetitorAlertSubmission schema validation (~4 tests)
- Dynamic threat scoring logic (~5 tests)
- Agent bridge competitor endpoints registration (~6 tests)
- Orchestrator agent-id reassignment + deep analysis handler (~4 tests)
- DEFAULT_AGENTS competitor-analyst entry + trend-analyzer cleanup (~3 tests)
- Rate limit tier for /competitors/full-analysis (~1 test)
- User-facing intelligence endpoints registration (~3 tests)
"""

from __future__ import annotations

import pytest


# ── ThreatScoreDetail Schema ─────────────────────────────────────

class TestThreatScoreDetailSchema:
    """Test ThreatScoreDetail Pydantic schema."""

    def test_valid_score(self):
        from app.schemas.competitors import ThreatScoreDetail

        detail = ThreatScoreDetail(
            calculated_score=3.5,
            engagement_growth_factor=0.6,
            content_overlap_factor=0.4,
            frequency_factor=0.3,
            follower_ratio_factor=0.2,
            reasoning="Growing fast",
        )
        assert detail.calculated_score == 3.5
        assert detail.is_overridden is False

    def test_overridden_flag(self):
        from app.schemas.competitors import ThreatScoreDetail

        detail = ThreatScoreDetail(
            calculated_score=4.0,
            is_overridden=True,
            reasoning="User override",
        )
        assert detail.is_overridden is True

    def test_score_below_minimum(self):
        from app.schemas.competitors import ThreatScoreDetail
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ThreatScoreDetail(calculated_score=0.5, reasoning="Too low")

    def test_score_above_maximum(self):
        from app.schemas.competitors import ThreatScoreDetail
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ThreatScoreDetail(calculated_score=5.5, reasoning="Too high")


# ── CompetitorAlert Schema ───────────────────────────────────────

class TestCompetitorAlertSchema:
    """Test CompetitorAlert Pydantic schema."""

    def test_valid_alert(self):
        from app.schemas.competitors import CompetitorAlert

        alert = CompetitorAlert(
            competitor_id="abc",
            competitor_name="Rival Co",
            alert_type="follower_surge",
            detail="Gained 10k followers in 24h",
            severity="high",
        )
        assert alert.alert_type == "follower_surge"
        assert alert.severity == "high"
        assert alert.metric_before is None

    def test_alert_with_metrics(self):
        from app.schemas.competitors import CompetitorAlert

        alert = CompetitorAlert(
            competitor_id="abc",
            competitor_name="Test",
            alert_type="engagement_drop",
            detail="Engagement dropped",
            metric_before=5.2,
            metric_after=2.1,
            severity="medium",
        )
        assert alert.metric_before == 5.2
        assert alert.metric_after == 2.1

    def test_invalid_alert_type(self):
        from app.schemas.competitors import CompetitorAlert
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorAlert(
                competitor_id="abc",
                competitor_name="Test",
                alert_type="invalid_type",
                detail="test",
            )

    def test_invalid_severity(self):
        from app.schemas.competitors import CompetitorAlert
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorAlert(
                competitor_id="abc",
                competitor_name="Test",
                alert_type="follower_surge",
                detail="test",
                severity="critical",
            )


# ── IntelligenceFeed Schema ──────────────────────────────────────

class TestIntelligenceFeedSchema:
    """Test IntelligenceFeed and IntelligenceFeedItem schemas."""

    def test_defaults(self):
        from app.schemas.competitors import IntelligenceFeed

        feed = IntelligenceFeed()
        assert feed.active_competitors == 0
        assert feed.avg_threat_level == 0.0
        assert feed.latest_analysis_date is None
        assert feed.open_alerts == 0
        assert feed.recent_analyses == []
        assert feed.recent_alerts == []
        assert feed.benchmarks == {}

    def test_populated_feed(self):
        from app.schemas.competitors import IntelligenceFeed, IntelligenceFeedItem

        item = IntelligenceFeedItem(
            item_type="analysis",
            competitor_id="abc",
            competitor_name="Rival",
            summary="Strong content strategy",
            threat_level=4,
            date="2026-02-27",
        )
        feed = IntelligenceFeed(
            active_competitors=3,
            avg_threat_level=3.2,
            recent_analyses=[item],
        )
        assert feed.active_competitors == 3
        assert len(feed.recent_analyses) == 1
        assert feed.recent_analyses[0].competitor_name == "Rival"


# ── CompetitorAlertSubmission Schema ─────────────────────────────

class TestCompetitorAlertSubmissionSchema:
    """Test CompetitorAlertSubmission (agent bridge) schema."""

    def test_valid_submission(self):
        from app.schemas.agent_bridge import CompetitorAlertSubmission

        sub = CompetitorAlertSubmission(
            agent_id="competitor-analyst",
            competitor_id="abc",
            alert_type="follower_surge",
            detail="Huge follower spike detected",
            severity="high",
        )
        assert sub.agent_id == "competitor-analyst"
        assert sub.severity == "high"

    def test_default_severity(self):
        from app.schemas.agent_bridge import CompetitorAlertSubmission

        sub = CompetitorAlertSubmission(
            agent_id="competitor-analyst",
            competitor_id="abc",
            alert_type="content_spike",
            detail="Content volume doubled this week",
        )
        assert sub.severity == "medium"

    def test_detail_max_length(self):
        from app.schemas.agent_bridge import CompetitorAlertSubmission
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorAlertSubmission(
                agent_id="competitor-analyst",
                competitor_id="abc",
                alert_type="follower_surge",
                detail="",  # empty detail
            )

    def test_optional_brand_id(self):
        from app.schemas.agent_bridge import CompetitorAlertSubmission

        sub = CompetitorAlertSubmission(
            agent_id="competitor-analyst",
            competitor_id="abc",
            alert_type="new_strategy",
            detail="Competitor pivoted to video content",
            brand_id="brand-123",
        )
        assert sub.brand_id == "brand-123"


# ── Threat Scoring Constants ─────────────────────────────────────

class TestThreatScoringConstants:
    """Test threat scoring weights and constants."""

    def test_weights_sum_to_one(self):
        from app.schemas.competitors import THREAT_WEIGHTS

        total = sum(THREAT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_four_factors(self):
        from app.schemas.competitors import THREAT_WEIGHTS

        expected = {"engagement_growth", "content_overlap", "frequency", "follower_ratio"}
        assert set(THREAT_WEIGHTS.keys()) == expected

    def test_valid_alert_types_match(self):
        from app.schemas.competitors import VALID_ALERT_TYPES
        from app.schemas.agent_bridge import VALID_COMPETITOR_ALERT_TYPES

        assert VALID_ALERT_TYPES == VALID_COMPETITOR_ALERT_TYPES


# ── Dynamic Threat Scoring Service ───────────────────────────────

class TestDynamicThreatScoring:
    """Test calculate_dynamic_threat function structure."""

    def test_function_exists(self):
        from app.services.competitor_intel import calculate_dynamic_threat
        assert callable(calculate_dynamic_threat)

    def test_function_signature(self):
        import inspect
        from app.services.competitor_intel import calculate_dynamic_threat
        sig = inspect.signature(calculate_dynamic_threat)
        assert "competitor_id" in sig.parameters
        assert "user_id" in sig.parameters

    def test_intelligence_feed_function_exists(self):
        from app.services.competitor_intel import get_intelligence_feed
        assert callable(get_intelligence_feed)

    def test_intelligence_feed_signature(self):
        import inspect
        from app.services.competitor_intel import get_intelligence_feed
        sig = inspect.signature(get_intelligence_feed)
        assert "user_id" in sig.parameters


# ── Agent Bridge Competitor Endpoints ────────────────────────────

class TestAgentBridgeCompetitorEndpoints:
    """Test agent bridge has all 6 competitor endpoints registered."""

    def _get_paths(self):
        from app.routers.agent_bridge import router
        return [r.path for r in router.routes if hasattr(r, "path")]

    def test_agent_competitors_list_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitors" in paths

    def test_agent_competitor_detail_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitors/{competitor_id}" in paths

    def test_agent_competitor_analyze_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitors/{competitor_id}/analyze" in paths

    def test_agent_competitor_refresh_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitors/{competitor_id}/refresh" in paths

    def test_agent_competitor_alerts_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitor-alerts" in paths

    def test_agent_competitive_landscape_endpoint(self):
        paths = self._get_paths()
        assert "/agent-api/competitive-landscape" in paths


# ── User-Facing Intelligence Endpoints ───────────────────────────

class TestUserFacingIntelligenceEndpoints:
    """Test user-facing intelligence endpoints are registered on competitors router."""

    def _get_paths(self):
        from app.routers.competitors import router
        return [r.path for r in router.routes if hasattr(r, "path")]

    def test_intelligence_endpoint(self):
        paths = self._get_paths()
        assert "/competitors/intelligence" in paths

    def test_alerts_endpoint(self):
        paths = self._get_paths()
        assert "/competitors/alerts" in paths

    def test_full_analysis_endpoint(self):
        from app.routers.competitors import router

        paths = self._get_paths()
        methods = {}
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                methods[route.path] = route.methods
        assert "/competitors/full-analysis" in paths
        assert "POST" in methods.get("/competitors/full-analysis", set())


# ── Rate Limit Tier ──────────────────────────────────────────────

class TestRateLimitTier:
    """Test rate limit assignment for full-analysis endpoint."""

    def test_full_analysis_uses_llm_tier(self):
        from app.middleware.rate_limit import _ROUTE_TIERS, TIER_LLM

        found = False
        for path, tier in _ROUTE_TIERS:
            if path == "/competitors/full-analysis":
                assert tier == TIER_LLM
                found = True
                break
        assert found, "/competitors/full-analysis not found in _ROUTE_TIERS"

    def test_full_analysis_before_generic_competitors(self):
        from app.middleware.rate_limit import _ROUTE_TIERS

        full_idx = None
        generic_idx = None
        for i, (path, _) in enumerate(_ROUTE_TIERS):
            if path == "/competitors/full-analysis":
                full_idx = i
            elif path == "/competitors":
                generic_idx = i
        assert full_idx is not None, "/competitors/full-analysis not in _ROUTE_TIERS"
        assert generic_idx is not None, "/competitors not in _ROUTE_TIERS"
        assert full_idx < generic_idx, "full-analysis must precede generic /competitors"


# ── Orchestrator Agent Reassignment ──────────────────────────────

class TestOrchestratorCompetitorUpdates:
    """Test orchestrator uses competitor-analyst for competitor tasks."""

    def test_weekly_competitor_uses_competitor_analyst(self):
        from app.services.agent_orchestrator import SCHEDULES

        sched = next(s for s in SCHEDULES if s["id"] == "weekly_competitor")
        assert sched["agent_id"] == "competitor-analyst"

    def test_daily_competitor_scan_uses_competitor_analyst(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        scan = next(s for s in DAILY_SCHEDULES if s["id"] == "daily_competitor_scan")
        assert scan["agent_id"] == "competitor-analyst"

    def test_competitor_handler_registered(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        assert "competitor" in handlers
        handler = handlers["competitor"]
        assert handler.__name__ == "_handle_competitor_deep_analysis"

    def test_deep_analysis_handler_callable(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        handler = handlers["competitor"]
        assert callable(handler)


# ── DEFAULT_AGENTS Updates ───────────────────────────────────────

class TestDefaultAgentsUpdates:
    """Test DEFAULT_AGENTS includes competitor-analyst and trend-analyzer is cleaned up."""

    def test_competitor_analyst_in_default_agents(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        ids = [a["id"] for a in DEFAULT_AGENTS]
        assert "competitor-analyst" in ids

    def test_competitor_analyst_skills(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        agent = next(a for a in DEFAULT_AGENTS if a["id"] == "competitor-analyst")
        assert "competitive-analysis" in agent["skills"]
        assert "threat-scoring" in agent["skills"]
        assert "benchmarking" in agent["skills"]
        assert agent["role"] == "Competitive Intelligence Specialist"

    def test_trend_analyzer_no_competitor_scan(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        agent = next(a for a in DEFAULT_AGENTS if a["id"] == "trend-analyzer")
        assert "competitor-scan" not in agent["skills"]

    def test_eight_default_agents(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        assert len(DEFAULT_AGENTS) == 8


# ── CompetitorOut Schema Update ──────────────────────────────────

class TestCompetitorOutOverrideField:
    """Test threat_level_override field on CompetitorOut."""

    def test_default_false(self):
        from app.schemas.competitors import CompetitorOut

        out = CompetitorOut(
            id="abc",
            user_id="user-1",
            name="Test",
            platform="website",
            profile_url="https://example.com",
        )
        assert out.threat_level_override is False

    def test_override_true(self):
        from app.schemas.competitors import CompetitorOut

        out = CompetitorOut(
            id="abc",
            user_id="user-1",
            name="Test",
            platform="website",
            profile_url="https://example.com",
            threat_level_override=True,
        )
        assert out.threat_level_override is True
