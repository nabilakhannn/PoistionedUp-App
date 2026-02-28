"""Tests for Slice 75: Competitor Intelligence Dashboard.

Covers:
- CompetitorCreate / CompetitorUpdate / CompetitorOut schema validation (~6 tests)
- CompetitorMetricRecord schema validation (~3 tests)
- CompetitorContentRecord schema validation (~3 tests)
- Router registration (prefix, tags, all endpoints) (~6 tests)
- Rate limit tier assignments (~3 tests)
- Service CRUD logic with mocked DB (~6 tests)
- Content gap analysis logic (~3 tests)
"""

from __future__ import annotations

import pytest


# ── Schema Tests: CompetitorCreate ──────────────────────────────

class TestCompetitorCreateSchema:
    """Test CompetitorCreate Pydantic schema."""

    def test_valid_create(self):
        from app.schemas.competitors import CompetitorCreate

        data = CompetitorCreate(
            name="Rival Co",
            platform="linkedin",
            profile_url="https://linkedin.com/company/rival",
            threat_level=4,
        )
        assert data.name == "Rival Co"
        assert data.platform == "linkedin"
        assert data.threat_level == 4

    def test_defaults(self):
        from app.schemas.competitors import CompetitorCreate

        data = CompetitorCreate(
            name="Test",
            profile_url="https://example.com",
        )
        assert data.platform == "website"
        assert data.threat_level == 3
        assert data.brand_id is None
        assert data.positioning is None

    def test_rejects_invalid_platform(self):
        from app.schemas.competitors import CompetitorCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorCreate(
                name="Test",
                platform="snapchat",
                profile_url="https://example.com",
            )

    def test_threat_level_range(self):
        from app.schemas.competitors import CompetitorCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorCreate(
                name="Test",
                profile_url="https://example.com",
                threat_level=0,
            )

        with pytest.raises(ValidationError):
            CompetitorCreate(
                name="Test",
                profile_url="https://example.com",
                threat_level=6,
            )

    def test_name_required(self):
        from app.schemas.competitors import CompetitorCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorCreate(
                profile_url="https://example.com",
            )

    def test_all_valid_platforms_accepted(self):
        from app.schemas.competitors import CompetitorCreate, VALID_PLATFORMS

        for platform in VALID_PLATFORMS:
            data = CompetitorCreate(
                name="Test",
                platform=platform,
                profile_url="https://example.com",
            )
            assert data.platform == platform


# ── Schema Tests: CompetitorUpdate ──────────────────────────────

class TestCompetitorUpdateSchema:
    """Test CompetitorUpdate Pydantic schema."""

    def test_partial_update(self):
        from app.schemas.competitors import CompetitorUpdate

        update = CompetitorUpdate(name="New Name", threat_level=5)
        assert update.name == "New Name"
        assert update.threat_level == 5
        assert update.platform is None

    def test_rejects_invalid_status(self):
        from app.schemas.competitors import CompetitorUpdate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorUpdate(status="deleted")

    def test_valid_status_values(self):
        from app.schemas.competitors import CompetitorUpdate

        for s in ("active", "archived"):
            update = CompetitorUpdate(status=s)
            assert update.status == s


# ── Schema Tests: CompetitorMetricRecord ────────────────────────

class TestCompetitorMetricRecordSchema:
    """Test CompetitorMetricRecord Pydantic schema."""

    def test_valid_metric(self):
        from app.schemas.competitors import CompetitorMetricRecord

        record = CompetitorMetricRecord(
            followers=5000,
            engagement_rate=3.5,
            post_frequency_weekly=4.0,
            top_topic="marketing",
        )
        assert record.followers == 5000
        assert record.engagement_rate == 3.5

    def test_defaults(self):
        from app.schemas.competitors import CompetitorMetricRecord

        record = CompetitorMetricRecord()
        assert record.followers is None
        assert record.source == "manual"

    def test_rejects_negative_engagement(self):
        from app.schemas.competitors import CompetitorMetricRecord
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorMetricRecord(engagement_rate=-1.0)


# ── Schema Tests: CompetitorContentRecord ───────────────────────

class TestCompetitorContentRecordSchema:
    """Test CompetitorContentRecord Pydantic schema."""

    def test_valid_content(self):
        from app.schemas.competitors import CompetitorContentRecord

        record = CompetitorContentRecord(
            title="How to grow on LinkedIn",
            url="https://linkedin.com/post/123",
            topics=["linkedin", "growth"],
            format="post",
        )
        assert record.title == "How to grow on LinkedIn"
        assert len(record.topics) == 2

    def test_format_default(self):
        from app.schemas.competitors import CompetitorContentRecord

        record = CompetitorContentRecord()
        assert record.format == "post"

    def test_rejects_invalid_format(self):
        from app.schemas.competitors import CompetitorContentRecord
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CompetitorContentRecord(format="podcast")

    def test_all_valid_formats(self):
        from app.schemas.competitors import CompetitorContentRecord, VALID_CONTENT_FORMATS

        for fmt in VALID_CONTENT_FORMATS:
            record = CompetitorContentRecord(format=fmt)
            assert record.format == fmt


# ── Schema Tests: Comparison / Analysis ─────────────────────────

class TestComparisonAnalysisSchemas:
    """Test comparison and analysis response schemas."""

    def test_comparison_model(self):
        from app.schemas.competitors import CompetitorComparison

        comp = CompetitorComparison(
            competitor_id="abc-123",
            competitor_name="Rival Co",
            user_metrics={"total_posts": 50},
            competitor_metrics={"followers": 10000},
            insights=["They post more frequently."],
        )
        assert comp.competitor_name == "Rival Co"
        assert len(comp.insights) == 1

    def test_analysis_report_model(self):
        from app.schemas.competitors import CompetitorAnalysisReport

        report = CompetitorAnalysisReport(
            competitor_id="abc-123",
            summary="Strong LinkedIn presence.",
            strengths=["Consistent posting"],
            weaknesses=["Low engagement"],
            content_pillars=["marketing", "sales"],
            threat_assessment="Medium",
        )
        assert report.summary == "Strong LinkedIn presence."
        assert len(report.strengths) == 1

    def test_content_gap_model(self):
        from app.schemas.competitors import ContentGap, ContentGapAnalysis

        gap = ContentGap(
            topic="SEO",
            covered_by_competitors=["Rival A", "Rival B"],
            your_coverage=False,
            priority="high",
        )
        analysis = ContentGapAnalysis(
            gaps=[gap],
            your_unique_topics=["personal branding"],
            shared_topics=["marketing"],
        )
        assert len(analysis.gaps) == 1
        assert analysis.gaps[0].priority == "high"


# ── Router Registration Tests ──────────────────────────────────

class TestCompetitorRouterRegistration:
    """Test that competitor routes are registered correctly."""

    def test_router_has_prefix(self):
        from app.routers.competitors import router

        assert router.prefix == "/competitors"

    def test_router_has_tag(self):
        from app.routers.competitors import router

        assert "competitors" in router.tags

    def test_has_list_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors" in routes

    def test_has_detail_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/{competitor_id}" in routes

    def test_has_metrics_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/{competitor_id}/metrics" in routes

    def test_has_refresh_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/{competitor_id}/refresh" in routes

    def test_has_analyze_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/{competitor_id}/analyze" in routes

    def test_has_comparison_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/comparison" in routes

    def test_has_gaps_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/gaps" in routes

    def test_has_content_endpoint(self):
        from app.routers.competitors import router

        routes = [r.path for r in router.routes]
        assert "/competitors/{competitor_id}/content" in routes


# ── Rate Limit Tests ───────────────────────────────────────────

class TestCompetitorRateLimits:
    """Test rate limit tiers for competitor endpoints."""

    def test_competitors_default_is_write_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_WRITE

        tier = _get_tier("/competitors", "GET")
        assert tier == TIER_WRITE

    def test_competitors_analyze_is_llm_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_LLM

        tier = _get_tier("/competitors/abc-123/analyze", "POST")
        assert tier == TIER_LLM

    def test_competitors_refresh_is_llm_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_LLM

        tier = _get_tier("/competitors/abc-123/refresh", "POST")
        assert tier == TIER_LLM


# ── Orchestrator Integration Tests ─────────────────────────────

class TestOrchestratorCompetitorIntegration:
    """Test competitor-related orchestrator additions."""

    def test_competitor_scan_handler_registered(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        assert "competitor_scan" in handlers

    def test_daily_competitor_scan_schedule_exists(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        ids = [s["id"] for s in DAILY_SCHEDULES]
        assert "daily_competitor_scan" in ids

    def test_daily_competitor_scan_schedule_config(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        scan = next(s for s in DAILY_SCHEDULES if s["id"] == "daily_competitor_scan")
        assert scan["task_type"] == "competitor_scan"
        assert scan["agent_id"] == "competitor-analyst"
        assert scan["cooldown_hours"] < 24


# ── Service Logic Tests (mocked DB) ───────────────────────────

class _MockResponse:
    """Minimal mock for Supabase responses."""

    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class _MockQuery:
    """Chainable mock for Supabase query builder."""

    def __init__(self, data=None):
        self._data = data or []

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        if isinstance(data, list):
            self._data = data
        else:
            self._data = [data]
        return self

    def update(self, data):
        if self._data:
            self._data = [{**self._data[0], **data}]
        return self

    def eq(self, *args):
        return self

    def in_(self, *args):
        return self

    def gte(self, *args):
        return self

    def lte(self, *args):
        return self

    def lt(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, n):
        return self

    def execute(self):
        return _MockResponse(self._data)


class _MockSupabase:
    """Mock Supabase client for service tests."""

    def __init__(self, table_data=None):
        self._table_data = table_data or {}

    def table(self, name):
        return _MockQuery(self._table_data.get(name, []))


class TestCompetitorServiceCRUD:
    """Test competitor service CRUD with mocked Supabase."""

    def test_create_competitor(self):
        from app.services.competitor_intel import create_competitor

        sb = _MockSupabase()
        result = create_competitor("user-1", {
            "name": "Rival Co",
            "profile_url": "https://example.com",
            "platform": "linkedin",
        }, sb)
        assert result["name"] == "Rival Co"
        assert result["user_id"] == "user-1"

    def test_list_competitors_returns_list(self):
        from app.services.competitor_intel import list_competitors

        sb = _MockSupabase({"competitors": [
            {"id": "c1", "name": "Rival A", "status": "active"},
            {"id": "c2", "name": "Rival B", "status": "active"},
        ]})
        result = list_competitors("user-1", sb)
        assert isinstance(result, list)

    def test_delete_competitor_soft_deletes(self):
        from app.services.competitor_intel import delete_competitor

        sb = _MockSupabase({"competitors": [
            {"id": "c1", "name": "Rival A", "status": "active"},
        ]})
        result = delete_competitor("c1", "user-1", sb)
        assert result is True

    def test_record_metrics(self):
        from app.services.competitor_intel import record_metrics

        sb = _MockSupabase()
        result = record_metrics("c1", {
            "followers": 5000,
            "engagement_rate": 3.5,
        }, sb)
        assert result["followers"] == 5000

    def test_record_content_batch(self):
        from app.services.competitor_intel import record_content

        sb = _MockSupabase()
        count = record_content("c1", [
            {"title": "Post 1", "format": "post"},
            {"title": "Post 2", "format": "video"},
        ], sb)
        assert count == 2

    def test_record_content_empty(self):
        from app.services.competitor_intel import record_content

        sb = _MockSupabase()
        count = record_content("c1", [], sb)
        assert count == 0


# ── Gap Analysis Logic Tests ──────────────────────────────────

class TestGapAnalysisLogic:
    """Test content gap analysis helper logic."""

    def test_comparison_insights_helper(self):
        from app.services.competitor_intel import _build_comparison_insights

        user_analytics = {
            "platforms": [{"avg_engagement_rate": 5.0}],
            "total_posts": 50,
        }
        comp_metrics = {
            "engagement_rate": 2.0,
            "post_frequency_weekly": 3.0,
        }
        insights = _build_comparison_insights(user_analytics, comp_metrics)
        assert any("higher" in i.lower() for i in insights)

    def test_comparison_insights_competitor_wins(self):
        from app.services.competitor_intel import _build_comparison_insights

        user_analytics = {
            "platforms": [{"avg_engagement_rate": 1.0}],
            "total_posts": 10,
        }
        comp_metrics = {
            "engagement_rate": 8.0,
            "post_frequency_weekly": 5.0,
        }
        insights = _build_comparison_insights(user_analytics, comp_metrics)
        assert any("competitor" in i.lower() or "higher" in i.lower() for i in insights)

    def test_comparison_insights_empty_data(self):
        from app.services.competitor_intel import _build_comparison_insights

        insights = _build_comparison_insights({}, {})
        assert len(insights) >= 1  # At least the "add more metrics" fallback
