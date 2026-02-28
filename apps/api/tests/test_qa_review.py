"""Tests for Slice 76: QA Agent — Content Quality Assurance.

Covers:
- QAReviewRequest schema validation (~4 tests)
- QAScoreBreakdown schema validation (~3 tests)
- QAReviewResult schema validation (~3 tests)
- QAStats schema validation (~2 tests)
- Router registration (prefix, tags, endpoints) (~5 tests)
- Rate limit tier assignments (~2 tests)
- Rule-based checks (forbidden words, hard bans, length, AI-tells) (~6 tests)
- Score aggregation logic (~4 tests)
- Auto-revision logic (~3 tests)
- Orchestrator integration (~3 tests)
- Service CRUD with mocked DB (~5 tests)
"""

from __future__ import annotations

import pytest


# ── Schema Tests: QAReviewRequest ─────────────────────────────

class TestQAReviewRequestSchema:
    """Test QAReviewRequest Pydantic schema."""

    def test_valid_request(self):
        from app.schemas.qa_review import QAReviewRequest

        req = QAReviewRequest(
            content_text="This is a great LinkedIn post about marketing.",
            platform="linkedin",
            content_ref_type="scheduled_item",
            content_ref_id="abc-123",
            brand_id="brand-1",
        )
        assert req.content_text.startswith("This is")
        assert req.platform == "linkedin"
        assert req.content_ref_type == "scheduled_item"

    def test_defaults(self):
        from app.schemas.qa_review import QAReviewRequest

        req = QAReviewRequest(content_text="Hello world")
        assert req.platform is None
        assert req.content_ref_type == "freeform"
        assert req.content_ref_id is None
        assert req.brand_id is None

    def test_content_text_required(self):
        from app.schemas.qa_review import QAReviewRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAReviewRequest()

    def test_rejects_invalid_ref_type(self):
        from app.schemas.qa_review import QAReviewRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAReviewRequest(
                content_text="Test content",
                content_ref_type="invalid_type",
            )


# ── Schema Tests: QAScoreBreakdown ────────────────────────────

class TestQAScoreBreakdownSchema:
    """Test QAScoreBreakdown Pydantic schema."""

    def test_valid_scores(self):
        from app.schemas.qa_review import QAScoreBreakdown

        scores = QAScoreBreakdown(
            voice_score=85,
            hook_score=70,
            structure_score=90,
            ai_tell_score=95,
            virality_score=60,
            goal_alignment_score=80,
        )
        assert scores.voice_score == 85
        assert scores.virality_score == 60

    def test_defaults_to_zero(self):
        from app.schemas.qa_review import QAScoreBreakdown

        scores = QAScoreBreakdown()
        assert scores.voice_score == 0
        assert scores.hook_score == 0
        assert scores.structure_score == 0
        assert scores.ai_tell_score == 0
        assert scores.virality_score == 0
        assert scores.goal_alignment_score == 0

    def test_rejects_out_of_range(self):
        from app.schemas.qa_review import QAScoreBreakdown
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAScoreBreakdown(voice_score=101)

        with pytest.raises(ValidationError):
            QAScoreBreakdown(hook_score=-1)


# ── Schema Tests: QAReviewResult ──────────────────────────────

class TestQAReviewResultSchema:
    """Test QAReviewResult Pydantic schema."""

    def test_valid_result(self):
        from app.schemas.qa_review import QAReviewResult, QAScoreBreakdown

        result = QAReviewResult(
            id="review-1",
            overall_score=82,
            scores=QAScoreBreakdown(
                voice_score=85, hook_score=80, structure_score=90,
                ai_tell_score=75, virality_score=70, goal_alignment_score=85,
            ),
            verdict="pass",
            feedback="Good content, well-structured.",
            issues=[],
            risk_flags=[],
            revision_number=0,
            created_at="2026-02-27T00:00:00Z",
        )
        assert result.overall_score == 82
        assert result.verdict == "pass"

    def test_valid_verdicts(self):
        from app.schemas.qa_review import QAReviewResult, QAScoreBreakdown

        for v in ("pass", "revise", "fail", "pending"):
            result = QAReviewResult(
                id="r-1", overall_score=50, verdict=v,
                scores=QAScoreBreakdown(), feedback="test",
                created_at="2026-01-01T00:00:00Z",
            )
            assert result.verdict == v

    def test_rejects_invalid_verdict(self):
        from app.schemas.qa_review import QAReviewResult, QAScoreBreakdown
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAReviewResult(
                id="r-1", overall_score=50, verdict="approved",
                scores=QAScoreBreakdown(), feedback="test",
                created_at="2026-01-01T00:00:00Z",
            )


# ── Schema Tests: QAIssue ─────────────────────────────────────

class TestQAIssueSchema:
    """Test QAIssue Pydantic schema."""

    def test_valid_issue(self):
        from app.schemas.qa_review import QAIssue

        issue = QAIssue(category="voice", severity="warning", detail="Tone mismatch")
        assert issue.category == "voice"

    def test_rejects_invalid_category(self):
        from app.schemas.qa_review import QAIssue
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAIssue(category="spelling", severity="warning", detail="test")

    def test_rejects_invalid_severity(self):
        from app.schemas.qa_review import QAIssue
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QAIssue(category="voice", severity="high", detail="test")


# ── Schema Tests: QAStats ─────────────────────────────────────

class TestQAStatsSchema:
    """Test QAStats Pydantic schema."""

    def test_valid_stats(self):
        from app.schemas.qa_review import QAStats

        stats = QAStats(
            total_reviews=100, pass_count=70, revise_count=20,
            fail_count=10, avg_score=75.5, avg_voice_score=80.0,
            avg_hook_score=72.0, avg_virality_score=68.0,
        )
        assert stats.total_reviews == 100
        assert stats.pass_count == 70

    def test_defaults(self):
        from app.schemas.qa_review import QAStats

        stats = QAStats()
        assert stats.total_reviews == 0
        assert stats.avg_score == 0.0
        assert stats.common_issues == []


# ── Router Registration Tests ─────────────────────────────────

class TestQARouterRegistration:
    """Test that QA routes are registered correctly."""

    def test_router_has_prefix(self):
        from app.routers.qa import router

        assert router.prefix == "/qa"

    def test_router_has_tag(self):
        from app.routers.qa import router

        assert "qa" in router.tags

    def test_has_review_endpoint(self):
        from app.routers.qa import router

        routes = [r.path for r in router.routes]
        assert "/qa/review" in routes

    def test_has_reviews_list_endpoint(self):
        from app.routers.qa import router

        routes = [r.path for r in router.routes]
        assert "/qa/reviews" in routes

    def test_has_stats_endpoint(self):
        from app.routers.qa import router

        routes = [r.path for r in router.routes]
        assert "/qa/stats" in routes


# ── Rate Limit Tests ──────────────────────────────────────────

class TestQARateLimits:
    """Test rate limit tiers for QA endpoints."""

    def test_qa_review_is_llm_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_LLM

        tier = _get_tier("/qa/review", "POST")
        assert tier == TIER_LLM

    def test_qa_reviews_list_is_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/qa/reviews", "GET")
        assert tier == TIER_READ

    def test_qa_stats_is_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/qa/stats", "GET")
        assert tier == TIER_READ


# ── Rule-Based Check Tests ────────────────────────────────────

class TestRuleBasedChecks:
    """Test the rule-based checking engine."""

    def test_detects_forbidden_words(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks("Let me delve into how we can leverage synergy to elevate your brand.")
        assert result["rule_scores"]["ai_tell"] < 100
        assert len(result["forbidden_found"]) >= 3
        assert any(i["category"] == "ai_tell" for i in result["issues"])

    def test_detects_em_dashes(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks("This is great \u2014 really amazing content.")
        assert any("dash" in i["detail"].lower() for i in result["issues"])
        assert result["rule_scores"]["ai_tell"] < 100

    def test_detects_semicolons(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks("First point; second point; third point.")
        assert any("semicolon" in i["detail"].lower() for i in result["issues"])

    def test_detects_reversal_patterns(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks("It is not just about writing, it is about connecting.")
        assert any("reversal" in i["detail"].lower() for i in result["issues"])

    def test_clean_content_passes(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks(
            "I spent 3 hours testing this new approach to LinkedIn posts. "
            "Here's what actually worked for my audience of B2B founders."
        )
        assert result["rule_scores"]["ai_tell"] >= 80
        assert len(result["forbidden_found"]) == 0

    def test_platform_length_validation(self):
        from app.services.qa_review import _run_rule_checks

        # Twitter should flag content > 280 chars
        long_text = "x" * 300
        result = _run_rule_checks(long_text, platform="twitter")
        assert any("exceeds" in i["detail"].lower() for i in result["issues"])

    def test_short_content_flagged(self):
        from app.services.qa_review import _run_rule_checks

        result = _run_rule_checks("Hi")
        assert any("too short" in i["detail"].lower() for i in result["issues"])
        assert result["rule_scores"]["structure"] < 100


# ── Score Aggregation Tests ───────────────────────────────────

class TestScoreAggregation:
    """Test the score aggregation logic."""

    def test_weighted_average_correct(self):
        from app.services.qa_review import _aggregate_scores

        rule_scores = {"ai_tell": 100, "structure": 100}
        llm_scores = {
            "voice_score": 80,
            "hook_score": 80,
            "structure_score": 80,
            "ai_tell_score": 80,
            "virality_score": 80,
            "goal_alignment_score": 80,
        }
        overall, breakdown = _aggregate_scores(rule_scores, llm_scores)
        assert overall == 80  # All 80 = weighted average 80

    def test_conservative_minimum(self):
        from app.services.qa_review import _aggregate_scores

        # Rule says 40, LLM says 90 → conservative min = 40
        rule_scores = {"ai_tell": 40, "structure": 50}
        llm_scores = {
            "voice_score": 90,
            "hook_score": 90,
            "structure_score": 90,
            "ai_tell_score": 90,
            "virality_score": 90,
            "goal_alignment_score": 90,
        }
        _, breakdown = _aggregate_scores(rule_scores, llm_scores)
        assert breakdown.ai_tell_score == 40  # min(40, 90)
        assert breakdown.structure_score == 50  # min(50, 90)

    def test_pass_threshold(self):
        from app.services.qa_review import _determine_verdict

        assert _determine_verdict(80) == "pass"
        assert _determine_verdict(100) == "pass"
        assert _determine_verdict(79) == "revise"

    def test_revise_threshold(self):
        from app.services.qa_review import _determine_verdict

        assert _determine_verdict(50) == "revise"
        assert _determine_verdict(79) == "revise"
        assert _determine_verdict(49) == "fail"

    def test_fail_threshold(self):
        from app.services.qa_review import _determine_verdict

        assert _determine_verdict(0) == "fail"
        assert _determine_verdict(49) == "fail"

    def test_perfect_score(self):
        from app.services.qa_review import _aggregate_scores

        rule_scores = {"ai_tell": 100, "structure": 100}
        llm_scores = {
            "voice_score": 100,
            "hook_score": 100,
            "structure_score": 100,
            "ai_tell_score": 100,
            "virality_score": 100,
            "goal_alignment_score": 100,
        }
        overall, _ = _aggregate_scores(rule_scores, llm_scores)
        assert overall == 100


# ── Score Weights Tests ───────────────────────────────────────

class TestScoreWeights:
    """Test that score weights sum to 1.0."""

    def test_weights_sum_to_one(self):
        from app.schemas.qa_review import SCORE_WEIGHTS

        total = sum(SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_voice_is_highest_weight(self):
        from app.schemas.qa_review import SCORE_WEIGHTS

        assert SCORE_WEIGHTS["voice"] == max(SCORE_WEIGHTS.values())


# ── Orchestrator Integration Tests ────────────────────────────

class TestOrchestratorQAIntegration:
    """Test QA-related orchestrator additions."""

    def test_qa_review_handler_registered(self):
        from app.services.agent_orchestrator import _get_handlers

        handlers = _get_handlers()
        assert "qa_review_pending" in handlers

    def test_daily_qa_review_schedule_exists(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        ids = [s["id"] for s in DAILY_SCHEDULES]
        assert "daily_qa_review" in ids

    def test_daily_qa_review_schedule_config(self):
        from app.services.agent_orchestrator import DAILY_SCHEDULES

        sched = next(s for s in DAILY_SCHEDULES if s["id"] == "daily_qa_review")
        assert sched["task_type"] == "qa_review_pending"
        assert sched["agent_id"] == "qa-reviewer"
        assert sched["cooldown_hours"] < 24


# ── Service Logic Tests (mocked DB) ──────────────────────────

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


class TestQAServiceLogic:
    """Test QA service functions with mocked DB."""

    def test_get_qa_stats_empty(self):
        from app.services.qa_review import get_qa_stats

        sb = _MockSupabase()
        stats = get_qa_stats("user-1", days=30, sb=sb)
        assert stats.total_reviews == 0
        assert stats.avg_score == 0.0

    def test_get_qa_stats_with_data(self):
        from app.services.qa_review import get_qa_stats

        sb = _MockSupabase({"qa_reviews": [
            {"overall_score": 90, "voice_score": 85, "hook_score": 80, "virality_score": 75, "verdict": "pass", "issues": []},
            {"overall_score": 60, "voice_score": 55, "hook_score": 50, "virality_score": 45, "verdict": "revise", "issues": [{"category": "ai_tell"}]},
            {"overall_score": 30, "voice_score": 25, "hook_score": 20, "virality_score": 15, "verdict": "fail", "issues": [{"category": "voice"}, {"category": "ai_tell"}]},
        ]})
        stats = get_qa_stats("user-1", days=30, sb=sb)
        assert stats.total_reviews == 3
        assert stats.pass_count == 1
        assert stats.revise_count == 1
        assert stats.fail_count == 1
        assert stats.avg_score == 60.0

    def test_list_reviews_returns_list(self):
        from app.services.qa_review import list_reviews

        sb = _MockSupabase({"qa_reviews": [
            {"id": "r1", "content_ref_type": "freeform", "overall_score": 85, "verdict": "pass", "created_at": "2026-02-27T00:00:00Z", "revision_number": 0},
            {"id": "r2", "content_ref_type": "scheduled_item", "overall_score": 55, "verdict": "revise", "created_at": "2026-02-26T00:00:00Z", "revision_number": 1},
        ]})
        results = list_reviews("user-1", days=30, sb=sb)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_get_review_found(self):
        from app.services.qa_review import get_review

        sb = _MockSupabase({"qa_reviews": [
            {"id": "r1", "overall_score": 85, "verdict": "pass"},
        ]})
        result = get_review("r1", "user-1", sb=sb)
        assert result is not None
        assert result["overall_score"] == 85

    def test_get_review_not_found(self):
        from app.services.qa_review import get_review

        sb = _MockSupabase()
        result = get_review("nonexistent", "user-1", sb=sb)
        assert result is None


# ── Constants Tests ───────────────────────────────────────────

class TestQAConstants:
    """Test QA constants are properly defined."""

    def test_thresholds(self):
        from app.schemas.qa_review import QA_PASS_THRESHOLD, QA_REVISE_THRESHOLD, QA_MAX_REVISIONS

        assert QA_PASS_THRESHOLD == 80
        assert QA_REVISE_THRESHOLD == 50
        assert QA_MAX_REVISIONS == 2

    def test_valid_verdicts(self):
        from app.schemas.qa_review import VALID_VERDICTS

        assert "pass" in VALID_VERDICTS
        assert "revise" in VALID_VERDICTS
        assert "fail" in VALID_VERDICTS
        assert "pending" in VALID_VERDICTS

    def test_valid_ref_types(self):
        from app.schemas.qa_review import VALID_REF_TYPES

        assert "scheduled_item" in VALID_REF_TYPES
        assert "deliverable" in VALID_REF_TYPES
        assert "workflow" in VALID_REF_TYPES
        assert "freeform" in VALID_REF_TYPES
