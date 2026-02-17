"""Tests for Performance Feedback system (Slice 12).

Unit tests for:
  - Engagement rate calculation
  - Performance tier calculation
  - User averages computation
  - Analytics aggregation
  - Pattern detection
  - Top hooks / anti-hooks
  - Performance context formatting for LLM injection
  - Schema validation
  - Post analysis prompt building
No external dependencies needed — all API calls are mocked.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Helpers ──────────────────────────────────────────────

def _make_post(
    post_id="post-1",
    user_id="user-456",
    title="How I got 100K subscribers",
    content_type="youtube_long",
    platform="youtube",
    hook_used="Most creators fail because they do X",
    hook_type="bold_claim",
    topic="subscriber growth",
    topic_category="growth_strategy",
    day_of_week="tuesday",
    views=10000,
    likes=500,
    comments=100,
    shares=50,
    saves=25,
    engagement_rate=0.0675,
    performance_tier="above_average",
    **kwargs,
):
    """Create a fake content_post row."""
    return {
        "id": post_id,
        "user_id": user_id,
        "title": title,
        "content_type": content_type,
        "platform": platform,
        "hook_used": hook_used,
        "hook_type": hook_type,
        "topic": topic,
        "topic_category": topic_category,
        "day_of_week": day_of_week,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_rate": engagement_rate,
        "performance_tier": performance_tier,
        "agent_analysis": {},
        "tags": [],
        "metadata": {},
        "content_body": None,
        "workflow_id": None,
        "collection_id": None,
        "published_url": None,
        "published_at": "2026-02-01T10:00:00+00:00",
        "language": "en",
        "watch_time_seconds": None,
        "click_through_rate": None,
        "impressions": None,
        "reach": None,
        "subscribers_gained": None,
        "created_at": "2026-02-01T10:00:00+00:00",
        "updated_at": "2026-02-01T10:00:00+00:00",
        **kwargs,
    }


def _make_sample_posts():
    """Create a set of posts for analytics testing."""
    return [
        _make_post(
            post_id="p1", hook_used="Story hooks are magic",
            hook_type="story", topic_category="storytelling",
            day_of_week="monday", views=20000, likes=1000,
            comments=200, shares=100, saves=50,
            engagement_rate=0.0675, performance_tier="viral",
        ),
        _make_post(
            post_id="p2", hook_used="Did you know 90% of X fail?",
            hook_type="statistic", topic_category="ai_tools",
            day_of_week="tuesday", views=10000, likes=400,
            comments=80, shares=30, saves=10,
            engagement_rate=0.052, performance_tier="above_average",
        ),
        _make_post(
            post_id="p3", hook_used="Everything about AI is wrong",
            hook_type="contrarian", topic_category="ai_tools",
            day_of_week="monday", views=8000, likes=200,
            comments=40, shares=10, saves=5,
            engagement_rate=0.031875, performance_tier="average",
        ),
        _make_post(
            post_id="p4", hook_used="My boring topic nobody cared about",
            hook_type="question", topic_category="personal_branding",
            day_of_week="friday", views=2000, likes=50,
            comments=10, shares=2, saves=1,
            engagement_rate=0.0315, performance_tier="below_average",
        ),
        _make_post(
            post_id="p5", hook_used="Generic post title",
            hook_type="question", topic_category="personal_branding",
            day_of_week="friday", views=500, likes=5,
            comments=1, shares=0, saves=0,
            engagement_rate=0.012, performance_tier="flop",
        ),
        _make_post(
            post_id="p6", hook_used="LinkedIn hot take on AI",
            hook_type="contrarian", topic_category="ai_tools",
            platform="linkedin", day_of_week="wednesday",
            views=5000, likes=300, comments=60, shares=40, saves=20,
            engagement_rate=0.084, performance_tier="viral",
        ),
    ]


# ── Engagement Rate ──────────────────────────────────────


class TestEngagementRate:
    def test_basic_calculation(self):
        from app.services.performance_analytics import calculate_engagement_rate
        er = calculate_engagement_rate(views=10000, likes=500, comments=100, shares=50, saves=25)
        assert er == pytest.approx(0.0675, abs=0.001)

    def test_zero_views_returns_none(self):
        from app.services.performance_analytics import calculate_engagement_rate
        assert calculate_engagement_rate(views=0, likes=10) is None

    def test_none_views_returns_none(self):
        from app.services.performance_analytics import calculate_engagement_rate
        assert calculate_engagement_rate(views=None, likes=10) is None

    def test_only_likes(self):
        from app.services.performance_analytics import calculate_engagement_rate
        er = calculate_engagement_rate(views=1000, likes=50)
        assert er == pytest.approx(0.05, abs=0.001)

    def test_all_none_metrics(self):
        from app.services.performance_analytics import calculate_engagement_rate
        er = calculate_engagement_rate(views=1000)
        assert er == pytest.approx(0.0, abs=0.001)


# ── Performance Tier ─────────────────────────────────────


class TestPerformanceTier:
    def test_viral_tier(self):
        from app.services.performance_analytics import calculate_performance_tier
        # 4x average = viral (using 0.20 / 0.05 = 4.0 to avoid float boundary)
        tier = calculate_performance_tier(
            engagement_rate=0.20, avg_engagement=0.05, total_user_posts=10
        )
        assert tier == "viral"

    def test_above_average_tier(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.08, avg_engagement=0.05, total_user_posts=10
        )
        assert tier == "above_average"

    def test_average_tier(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.05, avg_engagement=0.05, total_user_posts=10
        )
        assert tier == "average"

    def test_below_average_tier(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.02, avg_engagement=0.05, total_user_posts=10
        )
        assert tier == "below_average"

    def test_flop_tier(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.005, avg_engagement=0.05, total_user_posts=10
        )
        assert tier == "flop"

    def test_not_enough_posts(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.15, avg_engagement=0.05, total_user_posts=3
        )
        assert tier is None

    def test_none_engagement(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=None, avg_engagement=0.05, total_user_posts=10
        )
        assert tier is None

    def test_zero_average(self):
        from app.services.performance_analytics import calculate_performance_tier
        tier = calculate_performance_tier(
            engagement_rate=0.05, avg_engagement=0.0, total_user_posts=10
        )
        assert tier is None


# ── User Averages ────────────────────────────────────────


class TestUserAverages:
    def test_averages_all_platforms(self):
        from app.services.performance_analytics import get_user_averages
        posts = _make_sample_posts()
        avgs = get_user_averages(posts)
        assert avgs["post_count"] == 6
        assert avgs["avg_engagement_rate"] is not None
        assert avgs["avg_views"] is not None

    def test_averages_filtered_by_platform(self):
        from app.services.performance_analytics import get_user_averages
        posts = _make_sample_posts()
        avgs = get_user_averages(posts, platform="linkedin")
        assert avgs["post_count"] == 1
        assert avgs["avg_engagement_rate"] == pytest.approx(0.084, abs=0.001)

    def test_averages_empty_posts(self):
        from app.services.performance_analytics import get_user_averages
        avgs = get_user_averages([])
        assert avgs["post_count"] == 0
        assert avgs["avg_engagement_rate"] is None

    def test_averages_no_matching_platform(self):
        from app.services.performance_analytics import get_user_averages
        posts = _make_sample_posts()
        avgs = get_user_averages(posts, platform="tiktok")
        assert avgs["post_count"] == 0


# ── Analytics ────────────────────────────────────────────


class TestAnalytics:
    def test_full_analytics(self):
        from app.services.performance_analytics import get_analytics
        posts = _make_sample_posts()
        result = get_analytics(posts)
        assert result["total_posts"] == 6
        assert len(result["platforms"]) >= 2
        assert len(result["top_topics"]) >= 1
        assert len(result["top_hook_types"]) >= 1
        assert isinstance(result["top_hooks"], list)
        assert isinstance(result["anti_hooks"], list)

    def test_analytics_empty(self):
        from app.services.performance_analytics import get_analytics
        result = get_analytics([])
        assert result["total_posts"] == 0
        assert result["platforms"] == []

    def test_analytics_platform_breakdown(self):
        from app.services.performance_analytics import get_analytics
        posts = _make_sample_posts()
        result = get_analytics(posts)
        platforms = {p["platform"]: p for p in result["platforms"]}
        assert "youtube" in platforms
        assert "linkedin" in platforms
        assert platforms["youtube"]["post_count"] == 5
        assert platforms["linkedin"]["post_count"] == 1

    def test_analytics_top_hooks_ordered(self):
        from app.services.performance_analytics import get_analytics
        posts = _make_sample_posts()
        result = get_analytics(posts)
        # Top hooks should come from highest engagement posts
        if result["top_hooks"]:
            assert result["top_hooks"][0] in [
                "LinkedIn hot take on AI",
                "Story hooks are magic",
            ]

    def test_best_day_detected(self):
        from app.services.performance_analytics import get_analytics
        posts = _make_sample_posts()
        result = get_analytics(posts)
        # Monday has higher average engagement than friday
        assert result["best_day_of_week"] is not None


# ── Pattern Detection ────────────────────────────────────


class TestPatternDetection:
    def test_detects_hook_pattern(self):
        from app.services.performance_analytics import detect_patterns
        posts = _make_sample_posts()
        patterns = detect_patterns(posts)
        # Should detect that story hooks outperform question hooks
        hook_patterns = [p for p in patterns if "hooks" in p["pattern"].lower() and "outperform" in p["pattern"].lower()]
        assert len(hook_patterns) >= 1

    def test_detects_topic_pattern(self):
        from app.services.performance_analytics import detect_patterns
        posts = _make_sample_posts()
        patterns = detect_patterns(posts)
        topic_patterns = [p for p in patterns if "audience engages" in p["pattern"].lower()]
        assert len(topic_patterns) >= 1

    def test_no_patterns_few_posts(self):
        from app.services.performance_analytics import detect_patterns
        posts = [_make_post(post_id="p1")]
        patterns = detect_patterns(posts)
        assert patterns == []

    def test_pattern_has_confidence(self):
        from app.services.performance_analytics import detect_patterns
        posts = _make_sample_posts()
        patterns = detect_patterns(posts)
        for p in patterns:
            assert 0 <= p["confidence"] <= 1
            assert p["evidence"]


# ── Top/Anti Hooks ───────────────────────────────────────


class TestTopHooks:
    def test_top_hooks_limit(self):
        from app.services.performance_analytics import get_top_hooks
        posts = _make_sample_posts()
        hooks = get_top_hooks(posts, limit=3)
        assert len(hooks) <= 3

    def test_top_hooks_platform_filter(self):
        from app.services.performance_analytics import get_top_hooks
        posts = _make_sample_posts()
        hooks = get_top_hooks(posts, platform="linkedin")
        assert len(hooks) == 1
        assert "LinkedIn" in hooks[0]

    def test_anti_hooks(self):
        from app.services.performance_analytics import get_anti_hooks
        posts = _make_sample_posts()
        hooks = get_anti_hooks(posts, limit=2)
        assert len(hooks) <= 2


# ── Performance Context (LLM Injection) ─────────────────


class TestPerformanceContext:
    def test_context_with_data(self):
        from app.services.performance_analytics import get_performance_context
        posts = _make_sample_posts()
        context = get_performance_context(posts)
        assert "YOUR CONTENT PERFORMANCE DATA" in context
        assert "Based on 6 published posts" in context
        assert "TOP PERFORMING HOOKS" in context

    def test_context_empty_posts(self):
        from app.services.performance_analytics import get_performance_context
        context = get_performance_context([])
        assert "No performance data available" in context

    def test_context_platform_filter(self):
        from app.services.performance_analytics import get_performance_context
        posts = _make_sample_posts()
        context = get_performance_context(posts, platform="linkedin")
        assert "Based on 1 published posts" in context

    def test_context_includes_patterns(self):
        from app.services.performance_analytics import get_performance_context
        posts = _make_sample_posts()
        context = get_performance_context(posts)
        assert "DETECTED PATTERNS" in context

    def test_context_includes_anti_hooks(self):
        from app.services.performance_analytics import get_performance_context
        posts = _make_sample_posts()
        context = get_performance_context(posts)
        assert "HOOKS THAT FLOPPED" in context


# ── Schema Validation ────────────────────────────────────


class TestSchemas:
    def test_content_post_create_minimal(self):
        from app.schemas.performance import ContentPostCreate
        post = ContentPostCreate(
            title="Test Post",
            content_type="youtube_long",
            platform="youtube",
        )
        assert post.title == "Test Post"
        assert post.hook_used is None

    def test_content_post_create_full(self):
        from app.schemas.performance import ContentPostCreate
        post = ContentPostCreate(
            title="Full Post",
            content_type="linkedin_post",
            platform="linkedin",
            hook_used="My bold claim",
            hook_type="bold_claim",
            topic="AI tools",
            topic_category="ai_tools",
            tags=["ai", "tools"],
        )
        assert post.hook_type == "bold_claim"
        assert len(post.tags) == 2

    def test_content_post_create_empty_title_fails(self):
        from app.schemas.performance import ContentPostCreate
        with pytest.raises(Exception):
            ContentPostCreate(
                title="",
                content_type="youtube_long",
                platform="youtube",
            )

    def test_update_metrics_partial(self):
        from app.schemas.performance import ContentPostUpdateMetrics
        metrics = ContentPostUpdateMetrics(views=10000, likes=500)
        assert metrics.views == 10000
        assert metrics.comments is None

    def test_content_post_summary(self):
        from app.schemas.performance import ContentPostSummary
        summary = ContentPostSummary(
            id="p1",
            title="Test",
            content_type="youtube_long",
            platform="youtube",
            created_at="2026-01-01T00:00:00",
        )
        assert summary.performance_tier is None
        assert summary.engagement_rate is None

    def test_analytics_model(self):
        from app.schemas.performance import PerformanceAnalytics
        analytics = PerformanceAnalytics(
            total_posts=10,
            platforms=[],
            top_topics=[],
            top_hook_types=[],
            patterns=[],
            top_hooks=["hook1"],
            anti_hooks=[],
        )
        assert analytics.total_posts == 10

    def test_platform_breakdown(self):
        from app.schemas.performance import PlatformBreakdown
        pb = PlatformBreakdown(
            platform="youtube",
            post_count=5,
            avg_engagement_rate=0.05,
            top_tier_count=2,
        )
        assert pb.platform == "youtube"

    def test_pattern_detected(self):
        from app.schemas.performance import PatternDetected
        p = PatternDetected(
            pattern="Story hooks outperform question hooks by 2.3x",
            evidence="Avg engagement 6.75% vs 2.93%",
            confidence=0.8,
        )
        assert p.confidence == 0.8


# ── Post Analysis ────────────────────────────────────────


class TestPostAnalysis:
    @patch("worker.graph.llm.parse_json_response")
    @patch("worker.graph.llm.get_llm_client")
    def test_analyze_post_performance(self, mock_get_llm, mock_parse):
        from app.services.performance_analytics import analyze_post_performance

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.chat.return_value = {"content": '{"why_it_worked_or_failed": "test"}'}
        mock_parse.return_value = {
            "why_it_worked_or_failed": "Great hook + timely topic",
            "hook_assessment": "Strong curiosity gap",
            "topic_relevance": "High",
            "improvement_suggestions": ["Add more data"],
            "key_takeaway": "Story hooks work best",
        }

        post = _make_post()
        result = analyze_post_performance(post)

        assert result["why_it_worked_or_failed"] == "Great hook + timely topic"
        assert result["key_takeaway"] == "Story hooks work best"
        mock_llm.chat.assert_called_once()

    @patch("worker.graph.llm.parse_json_response")
    @patch("worker.graph.llm.get_llm_client")
    def test_analyze_post_includes_metrics_in_prompt(self, mock_get_llm, mock_parse):
        from app.services.performance_analytics import analyze_post_performance

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.chat.return_value = {"content": "{}"}
        mock_parse.return_value = {}

        post = _make_post(views=50000, performance_tier="viral")
        analyze_post_performance(post)

        call_args = mock_llm.chat.call_args
        user_msg = call_args[1]["messages"][1]["content"] if "messages" in call_args[1] else call_args[0][0][1]["content"]
        # The user prompt should contain the metrics
        assert "50000" in user_msg or "Views: 50000" in user_msg


# ── Pipeline Integration ─────────────────────────────────


class TestPipelineIntegration:
    def test_gap_analysis_fetch_perf_context_graceful(self):
        """_fetch_performance_context should return empty string on failure."""
        from worker.graph.nodes.gap_analysis import _fetch_performance_context
        # With no user_id, should return empty
        result = _fetch_performance_context("")
        assert result == ""

    def test_hook_lab_fetch_perf_context_graceful(self):
        from worker.graph.nodes.hook_lab import _fetch_performance_context
        result = _fetch_performance_context("")
        assert result == ""

    def test_script_gen_fetch_perf_context_graceful(self):
        from worker.graph.nodes.script_generation import _fetch_performance_context
        result = _fetch_performance_context("")
        assert result == ""

    @patch("app.deps.get_admin_client")
    def test_fetch_perf_context_no_posts(self, mock_admin):
        from worker.graph.nodes.gap_analysis import _fetch_performance_context

        mock_client = MagicMock()
        mock_admin.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_resp

        result = _fetch_performance_context("user-123")
        assert result == ""

    @patch("app.deps.get_admin_client")
    def test_fetch_perf_context_with_posts(self, mock_admin):
        from worker.graph.nodes.gap_analysis import _fetch_performance_context

        mock_client = MagicMock()
        mock_admin.return_value = mock_client
        posts = _make_sample_posts()
        mock_resp = MagicMock()
        mock_resp.data = posts
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_resp

        result = _fetch_performance_context("user-123")
        assert "YOUR CONTENT PERFORMANCE DATA" in result

    def test_brand_chat_fetch_perf_context_graceful(self):
        from app.services.brand_chat import _fetch_performance_context
        result = _fetch_performance_context("")
        assert result == ""

    def test_build_chat_messages_with_perf_context(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages(
            "ica",
            [{"role": "user", "content": "hello"}],
            resource_context="some resources",
            performance_context="--- YOUR CONTENT PERFORMANCE DATA ---\nBased on 10 posts",
        )
        assert len(messages) == 2  # system + user
        assert "YOUR CONTENT PERFORMANCE DATA" in messages[0]["content"]
        assert "RELEVANT KNOWLEDGE" in messages[0]["content"]

    def test_build_chat_messages_without_perf_context(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("ica", [{"role": "user", "content": "hi"}])
        assert "YOUR CONTENT PERFORMANCE DATA" not in messages[0]["content"]
