"""Slice 112 — Analytics & ROI Dashboard tests.

Tests 1-21: Pure service function tests (no mocking needed).
Tests 22-25: Router structural tests.
"""

import pytest

from app.services.analytics_dashboard import (
    compute_content_roi,
    compute_cost_tracking,
    compute_engagement_trends,
    compute_lead_funnel,
    compute_pipeline_performance,
    compute_revenue_attribution,
)


# ── compute_content_roi ──────────────────────────────────────────────────


class TestContentROI:
    def test_empty_deliverables(self):
        result = compute_content_roi([], 30)
        assert result["total_generated"] == 0
        assert result["posts_per_day"] == 0.0
        assert result["approval_rate"] == 0.0
        assert result["avg_qa_score"] == 0.0
        assert result["daily_breakdown"] == []

    def test_mixed_statuses(self):
        deliverables = [
            {"status": "approved", "qa_score": 85, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "approved", "qa_score": 90, "created_at": "2026-03-01T11:00:00Z"},
            {"status": "rejected", "qa_score": 45, "created_at": "2026-03-02T10:00:00Z"},
            {"status": "review", "qa_score": 70, "created_at": "2026-03-02T12:00:00Z"},
        ]
        result = compute_content_roi(deliverables, 30)
        assert result["total_generated"] == 4
        assert result["approved"] == 2
        assert result["rejected"] == 1
        assert result["in_review"] == 1
        assert result["approval_rate"] == 50.0

    def test_daily_breakdown_sorted(self):
        deliverables = [
            {"status": "approved", "qa_score": 80, "created_at": "2026-03-02T10:00:00Z"},
            {"status": "approved", "qa_score": 90, "created_at": "2026-03-01T10:00:00Z"},
        ]
        result = compute_content_roi(deliverables, 7)
        breakdown = result["daily_breakdown"]
        assert len(breakdown) == 2
        assert breakdown[0]["date"] == "2026-03-01"
        assert breakdown[1]["date"] == "2026-03-02"

    def test_posts_per_day(self):
        deliverables = [
            {"status": "approved", "created_at": f"2026-03-0{i}T10:00:00Z"}
            for i in range(1, 8)
        ]
        result = compute_content_roi(deliverables, 7)
        assert result["posts_per_day"] == 1.0

    def test_qa_score_excludes_zeroes(self):
        deliverables = [
            {"status": "approved", "qa_score": 80, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "approved", "qa_score": 0, "created_at": "2026-03-01T11:00:00Z"},
            {"status": "approved", "qa_score": None, "created_at": "2026-03-01T12:00:00Z"},
        ]
        result = compute_content_roi(deliverables, 7)
        assert result["avg_qa_score"] == 80.0


# ── compute_pipeline_performance ──────────────────────────────────────────


class TestPipelinePerformance:
    def test_empty_runs(self):
        result = compute_pipeline_performance([])
        assert result["total_runs"] == 0
        assert result["success_rate"] == 0.0
        assert result["avg_duration_ms"] == 0

    def test_success_rate(self):
        runs = [
            {"status": "completed", "task_type": "research", "duration_ms": 1000, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "completed", "task_type": "write", "duration_ms": 2000, "created_at": "2026-03-01T11:00:00Z"},
            {"status": "failed", "task_type": "qa", "duration_ms": 500, "created_at": "2026-03-01T12:00:00Z"},
        ]
        result = compute_pipeline_performance(runs)
        assert result["total_runs"] == 3
        assert result["completed"] == 2
        assert result["failed"] == 1
        assert result["success_rate"] == 66.7

    def test_phase_breakdown(self):
        runs = [
            {"status": "completed", "task_type": "research", "duration_ms": 1000, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "completed", "task_type": "research", "duration_ms": 3000, "created_at": "2026-03-02T10:00:00Z"},
            {"status": "failed", "task_type": "write", "duration_ms": 2000, "created_at": "2026-03-01T11:00:00Z"},
        ]
        result = compute_pipeline_performance(runs)
        assert result["phase_breakdown"]["research"]["count"] == 2
        assert result["phase_breakdown"]["research"]["avg_ms"] == 2000
        assert result["phase_breakdown"]["write"]["fail_count"] == 1

    def test_avg_duration(self):
        runs = [
            {"status": "completed", "task_type": "research", "duration_ms": 1000, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "completed", "task_type": "write", "duration_ms": 3000, "created_at": "2026-03-01T11:00:00Z"},
        ]
        result = compute_pipeline_performance(runs)
        assert result["avg_duration_ms"] == 2000


# ── compute_revenue_attribution ──────────────────────────────────────────


class TestRevenueAttribution:
    def test_empty(self):
        result = compute_revenue_attribution([])
        assert result["total_closed_won"] == 0
        assert result["win_rate"] == 0.0
        assert result["total_proposals_sent"] == 0

    def test_funnel_counts(self):
        deliverables = [
            {"client_brand": True, "proposal_status": "draft"},
            {"client_brand": True, "proposal_status": "sent"},
            {"client_brand": True, "proposal_status": "sent"},
            {"client_brand": True, "proposal_status": "closed_won", "deal_value": 5000},
            {"client_brand": True, "proposal_status": "closed_lost"},
        ]
        result = compute_revenue_attribution(deliverables)
        assert result["proposal_funnel"]["draft"] == 1
        assert result["proposal_funnel"]["sent"] == 2
        assert result["proposal_funnel"]["closed_won"] == 1
        assert result["proposal_funnel"]["closed_lost"] == 1
        assert result["total_closed_won"] == 5000.0
        assert result["total_proposals_sent"] == 4  # sent + accepted + rejected + won + lost

    def test_win_rate(self):
        deliverables = [
            {"client_brand": True, "proposal_status": "closed_won", "deal_value": 1000},
            {"client_brand": True, "proposal_status": "closed_won", "deal_value": 2000},
            {"client_brand": True, "proposal_status": "closed_lost"},
        ]
        result = compute_revenue_attribution(deliverables)
        assert result["win_rate"] == 66.7
        assert result["total_closed_won"] == 3000.0

    def test_win_rate_zero_division(self):
        deliverables = [
            {"client_brand": True, "proposal_status": "draft"},
        ]
        result = compute_revenue_attribution(deliverables)
        assert result["win_rate"] == 0.0

    def test_ignores_non_client_brands(self):
        deliverables = [
            {"client_brand": False, "proposal_status": "closed_won", "deal_value": 9999},
            {"client_brand": True, "proposal_status": "closed_won", "deal_value": 500},
        ]
        result = compute_revenue_attribution(deliverables)
        assert result["total_closed_won"] == 500.0


# ── compute_engagement_trends ─────────────────────────────────────────────


class TestEngagementTrends:
    def test_empty(self):
        result = compute_engagement_trends([])
        assert result["avg_engagement_rate"] == 0.0
        assert result["total_views"] == 0
        assert result["top_posts"] == []

    def test_hook_type_performance(self):
        posts = [
            {"hook_type": "pain", "engagement_rate": 0.05, "views": 100, "likes": 5, "comments": 2},
            {"hook_type": "pain", "engagement_rate": 0.10, "views": 200, "likes": 20, "comments": 5},
            {"hook_type": "curiosity", "engagement_rate": 0.03, "views": 50, "likes": 1, "comments": 0},
        ]
        result = compute_engagement_trends(posts)
        hook_perf = result["hook_type_performance"]
        assert len(hook_perf) == 2
        # Pain should be first (higher avg)
        assert hook_perf[0]["hook_type"] == "pain"
        assert hook_perf[0]["count"] == 2

    def test_top_posts_capped_at_5(self):
        posts = [
            {"title": f"Post {i}", "engagement_rate": i * 0.01, "views": 100, "likes": 10, "comments": 1, "platform": "linkedin", "hook_type": "pain", "published_at": "2026-03-01"}
            for i in range(1, 10)
        ]
        result = compute_engagement_trends(posts)
        assert len(result["top_posts"]) == 5
        # Highest engagement first
        assert result["top_posts"][0]["title"] == "Post 9"

    def test_tier_distribution(self):
        posts = [
            {"performance_tier": "viral", "engagement_rate": 0.1, "views": 1000, "likes": 100, "comments": 50},
            {"performance_tier": "viral", "engagement_rate": 0.12, "views": 1200, "likes": 120, "comments": 60},
            {"performance_tier": "average", "engagement_rate": 0.02, "views": 100, "likes": 2, "comments": 0},
        ]
        result = compute_engagement_trends(posts)
        assert result["tier_distribution"]["viral"] == 2
        assert result["tier_distribution"]["average"] == 1

    def test_topic_performance(self):
        posts = [
            {"topic_category": "marketing", "engagement_rate": 0.08, "views": 100, "likes": 8, "comments": 0},
            {"topic_category": "sales", "engagement_rate": 0.04, "views": 80, "likes": 3, "comments": 1},
        ]
        result = compute_engagement_trends(posts)
        assert len(result["topic_performance"]) == 2
        assert result["topic_performance"][0]["topic_category"] == "marketing"

    def test_best_posting_days(self):
        posts = [
            {"day_of_week": "Monday", "engagement_rate": 0.06, "views": 100, "likes": 6, "comments": 0},
            {"day_of_week": "Monday", "engagement_rate": 0.08, "views": 120, "likes": 10, "comments": 0},
            {"day_of_week": "Friday", "engagement_rate": 0.03, "views": 50, "likes": 1, "comments": 0},
        ]
        result = compute_engagement_trends(posts)
        assert result["best_posting_days"][0]["day_of_week"] == "Monday"


# ── compute_lead_funnel ───────────────────────────────────────────────────


class TestLeadFunnel:
    def test_empty(self):
        result = compute_lead_funnel([])
        assert result["total_leads"] == 0
        assert result["conversion_rate"] == 0.0

    def test_status_distribution(self):
        leads = [
            {"status": "cold", "bant_score": 2, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "cold", "bant_score": 1, "created_at": "2026-03-02T10:00:00Z"},
            {"status": "warm", "bant_score": 3, "created_at": "2026-03-03T10:00:00Z"},
            {"status": "customer", "bant_score": 4, "created_at": "2026-03-04T10:00:00Z"},
        ]
        result = compute_lead_funnel(leads)
        assert result["status_distribution"]["cold"] == 2
        assert result["status_distribution"]["warm"] == 1
        assert result["status_distribution"]["customer"] == 1
        assert result["total_leads"] == 4

    def test_bant_distribution(self):
        leads = [
            {"status": "cold", "bant_score": 2, "created_at": "2026-03-01T10:00:00Z"},
            {"status": "warm", "bant_score": 3, "created_at": "2026-03-02T10:00:00Z"},
            {"status": "warm", "bant_score": 3, "created_at": "2026-03-03T10:00:00Z"},
        ]
        result = compute_lead_funnel(leads)
        assert result["bant_distribution"]["2"] == 1
        assert result["bant_distribution"]["3"] == 2

    def test_conversion_rate_excludes_disqualified(self):
        leads = [
            {"status": "customer", "created_at": "2026-03-01T10:00:00Z"},
            {"status": "cold", "created_at": "2026-03-02T10:00:00Z"},
            {"status": "disqualified", "created_at": "2026-03-03T10:00:00Z"},
        ]
        result = compute_lead_funnel(leads)
        # 1 customer / 2 eligible (3 total - 1 disqualified) = 50%
        assert result["conversion_rate"] == 50.0

    def test_new_leads_period(self):
        leads = [
            {"status": "cold", "created_at": "2026-02-15T10:00:00Z"},  # before cutoff
            {"status": "cold", "created_at": "2026-03-01T10:00:00Z"},  # after cutoff
            {"status": "warm", "created_at": "2026-03-04T10:00:00Z"},  # after cutoff
        ]
        result = compute_lead_funnel(leads, period_start="2026-02-28")
        assert result["new_leads_period"] == 2


# ── compute_cost_tracking ────────────────────────────────────────────────


class TestCostTracking:
    def test_empty(self):
        result = compute_cost_tracking([], 20.0, 0)
        assert result["total_tokens"] == 0
        assert result["estimated_cost"] == 0.0
        assert result["cost_per_content"] == 0.0

    def test_token_estimation(self):
        runs = [
            {"total_tokens": 10000, "created_at": "2026-03-01T10:00:00Z"},
            {"total_tokens": 5000, "created_at": "2026-03-02T10:00:00Z"},
        ]
        result = compute_cost_tracking(runs, 20.0, 5)
        assert result["total_tokens"] == 15000
        # 15000 / 1000 * 0.003 = 0.045, round(0.045, 2) = 0.04 (banker's rounding)
        assert result["estimated_cost"] == 0.04
        assert result["cost_per_content"] == 0.008  # 0.04 / 5 rounded to 3 dp

    def test_budget_utilization(self):
        runs = [{"total_tokens": 100000, "created_at": "2026-03-01T10:00:00Z"}]
        result = compute_cost_tracking(runs, 1.0, 1)
        # 100000/1000 * 0.003 = $0.30, util = 0.30/1.0*100 = 30%
        assert result["budget_utilization"] == 30.0

    def test_daily_spend(self):
        runs = [
            {"total_tokens": 5000, "created_at": "2026-03-01T10:00:00Z"},
            {"total_tokens": 3000, "created_at": "2026-03-01T12:00:00Z"},
            {"total_tokens": 2000, "created_at": "2026-03-02T10:00:00Z"},
        ]
        result = compute_cost_tracking(runs, 20.0, 2)
        spend = result["daily_spend"]
        assert len(spend) == 2
        assert spend[0]["date"] == "2026-03-01"
        assert spend[0]["tokens"] == 8000
        assert spend[1]["date"] == "2026-03-02"
        assert spend[1]["tokens"] == 2000


# ── Router structural tests ──────────────────────────────────────────────


class TestRouterStructure:
    def test_endpoint_exists(self):
        from app.routers.analytics_dashboard import router

        paths = [r.path for r in router.routes]
        assert "/analytics/dashboard" in paths

    def test_jwt_auth_required(self):
        from app.routers.analytics_dashboard import analytics_dashboard
        import inspect

        sig = inspect.signature(analytics_dashboard)
        params = list(sig.parameters.values())
        param_names = [p.name for p in params]
        assert "user" in param_names

    def test_period_validation(self):
        from app.routers.analytics_dashboard import _VALID_PERIODS

        assert "7d" in _VALID_PERIODS
        assert "30d" in _VALID_PERIODS
        assert "90d" in _VALID_PERIODS
        assert "1d" not in _VALID_PERIODS

    def test_response_model_has_all_sections(self):
        from app.routers.analytics_dashboard import AnalyticsDashboardResponse

        fields = set(AnalyticsDashboardResponse.model_fields.keys())
        expected = {"period", "period_start", "period_end", "content_roi", "pipeline", "revenue", "engagement", "leads", "cost"}
        assert expected.issubset(fields)
