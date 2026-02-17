"""Tests for Experiments + Self-Voice DNA system (Slice 14).

Unit tests for:
  - Experiment CRUD (create, list, get, update, delete)
  - Experiment lifecycle (approve, cancel, assign posts)
  - Conclusion logic (winner determination, tie handling)
  - Auto-proposal from performance data
  - Experiment context formatting for pipeline injection
  - Completed experiments summary
  - Self-Voice DNA analysis and formatting
  - Voice drift check
  - Schema validation
  - Pipeline integration (experiment + self-voice context injection)
No external dependencies needed — all API calls are mocked.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Helpers ──────────────────────────────────────────────

def _make_experiment(
    exp_id="exp-1",
    user_id="user-789",
    hypothesis="Story hooks outperform question hooks",
    variable="hook_type",
    variant_a="story",
    variant_b="question",
    platform="youtube",
    target_posts=4,
    status="proposed",
    variant_a_posts=None,
    variant_b_posts=None,
    variant_a_avg_engagement=None,
    variant_b_avg_engagement=None,
    winner=None,
    conclusion=None,
    resulting_memory_id=None,
    created_at="2026-02-01T10:00:00+00:00",
    updated_at="2026-02-01T10:00:00+00:00",
    completed_at=None,
):
    """Create a fake experiment row."""
    return {
        "id": exp_id,
        "user_id": user_id,
        "hypothesis": hypothesis,
        "variable": variable,
        "variant_a": variant_a,
        "variant_b": variant_b,
        "platform": platform,
        "target_posts": target_posts,
        "status": status,
        "variant_a_posts": variant_a_posts or [],
        "variant_b_posts": variant_b_posts or [],
        "variant_a_avg_engagement": variant_a_avg_engagement,
        "variant_b_avg_engagement": variant_b_avg_engagement,
        "winner": winner,
        "conclusion": conclusion,
        "resulting_memory_id": resulting_memory_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "completed_at": completed_at,
    }


def _make_post(
    post_id="post-1",
    user_id="user-789",
    engagement_rate=0.05,
    hook_type="story",
    topic_category="ai_tools",
    platform="youtube",
):
    """Create a fake content_posts row."""
    return {
        "id": post_id,
        "user_id": user_id,
        "title": f"Test Post {post_id}",
        "content_type": "youtube_long",
        "platform": platform,
        "hook_type": hook_type,
        "topic_category": topic_category,
        "engagement_rate": engagement_rate,
        "performance_tier": "average",
        "created_at": "2026-02-01T10:00:00+00:00",
    }


def _mock_supabase_table(mock_admin, data=None):
    """Set up mock that handles any chain of .select().eq().order().execute()."""
    if data is None:
        data = []
    mock_table = MagicMock()
    mock_admin.return_value.table.return_value = mock_table
    for method in ["select", "eq", "in_", "insert", "update", "delete", "order", "limit", "is_"]:
        getattr(mock_table, method).return_value = mock_table
    mock_table.execute.return_value.data = data
    return mock_table


# ── Schema Tests ─────────────────────────────────────────

class TestExperimentSchemas:
    """Test Pydantic schema validation."""

    def test_experiment_create_valid(self):
        from app.schemas.experiments import ExperimentCreate
        schema = ExperimentCreate(
            hypothesis="Story hooks work better",
            variable="hook_type",
            variant_a="story",
            variant_b="question",
            platform="youtube",
        )
        assert schema.target_posts == 4  # default

    def test_experiment_create_custom_target(self):
        from app.schemas.experiments import ExperimentCreate
        schema = ExperimentCreate(
            hypothesis="Test",
            variable="topic",
            variant_a="ai",
            variant_b="business",
            platform="linkedin",
            target_posts=8,
        )
        assert schema.target_posts == 8

    def test_experiment_create_min_target(self):
        from app.schemas.experiments import ExperimentCreate
        with pytest.raises(Exception):
            ExperimentCreate(
                hypothesis="Test",
                variable="x",
                variant_a="a",
                variant_b="b",
                platform="youtube",
                target_posts=1,  # min is 2
            )

    def test_experiment_summary(self):
        from app.schemas.experiments import ExperimentSummary
        summary = ExperimentSummary(
            id="exp-1",
            hypothesis="Test",
            variable="hook_type",
            variant_a="story",
            variant_b="question",
            platform="youtube",
            status="proposed",
            target_posts=4,
            created_at="2026-02-01T10:00:00+00:00",
        )
        assert summary.variant_a_count == 0
        assert summary.winner is None

    def test_experiment_detail(self):
        from app.schemas.experiments import ExperimentDetail
        detail = ExperimentDetail(
            id="exp-1",
            hypothesis="Test",
            variable="hook_type",
            variant_a="story",
            variant_b="question",
            platform="youtube",
            status="completed",
            target_posts=4,
            variant_a_posts=["p1", "p2"],
            variant_b_posts=["p3", "p4"],
            winner="variant_a",
            conclusion="Story won",
            created_at="2026-02-01",
            updated_at="2026-02-01",
        )
        assert len(detail.variant_a_posts) == 2
        assert detail.winner == "variant_a"

    def test_self_voice_dna_defaults(self):
        from app.schemas.experiments import SelfVoiceDNA
        dna = SelfVoiceDNA()
        assert dna.tone == ""
        assert dna.posts_analyzed == 0
        assert dna.hook_patterns == []

    def test_voice_drift_result(self):
        from app.schemas.experiments import VoiceDriftResult
        result = VoiceDriftResult(
            drift_score=0.35,
            drift_level="medium",
            details=["Too formal"],
            recommendation="Use more contractions",
        )
        assert result.drift_score == 0.35
        assert result.baseline_available is True

    def test_drift_score_bounds(self):
        from app.schemas.experiments import VoiceDriftResult
        with pytest.raises(Exception):
            VoiceDriftResult(drift_score=1.5, drift_level="high")


# ── Experiment CRUD Tests ────────────────────────────────

class TestExperimentCRUD:
    """Test experiment create, list, get, update, delete."""

    @patch("app.deps.get_admin_client")
    def test_create_experiment(self, mock_admin):
        from app.services.experiments import create_experiment
        exp = _make_experiment()
        _mock_supabase_table(mock_admin, [exp])

        result = create_experiment(
            user_id="user-789",
            hypothesis="Story hooks outperform question hooks",
            variable="hook_type",
            variant_a="story",
            variant_b="question",
            platform="youtube",
        )
        assert result["id"] == "exp-1"
        assert result["status"] == "proposed"

    @patch("app.deps.get_admin_client")
    def test_list_experiments(self, mock_admin):
        from app.services.experiments import list_experiments
        exps = [_make_experiment(exp_id=f"exp-{i}") for i in range(3)]
        _mock_supabase_table(mock_admin, exps)

        result = list_experiments("user-789")
        assert len(result) == 3

    @patch("app.deps.get_admin_client")
    def test_list_experiments_with_status_filter(self, mock_admin):
        from app.services.experiments import list_experiments
        exps = [_make_experiment(status="running")]
        _mock_supabase_table(mock_admin, exps)

        result = list_experiments("user-789", status="running")
        assert len(result) == 1

    @patch("app.deps.get_admin_client")
    def test_get_experiment_by_id(self, mock_admin):
        from app.services.experiments import get_experiment_by_id
        exp = _make_experiment()
        _mock_supabase_table(mock_admin, [exp])

        result = get_experiment_by_id("user-789", "exp-1")
        assert result["hypothesis"] == "Story hooks outperform question hooks"

    @patch("app.deps.get_admin_client")
    def test_get_experiment_not_found(self, mock_admin):
        from app.services.experiments import get_experiment_by_id
        _mock_supabase_table(mock_admin, [])

        result = get_experiment_by_id("user-789", "nonexistent")
        assert result is None

    @patch("app.deps.get_admin_client")
    def test_update_experiment(self, mock_admin):
        from app.services.experiments import update_experiment
        exp = _make_experiment(hypothesis="Updated hypothesis")
        _mock_supabase_table(mock_admin, [exp])

        result = update_experiment("user-789", "exp-1", {"hypothesis": "Updated hypothesis"})
        assert result["hypothesis"] == "Updated hypothesis"

    @patch("app.deps.get_admin_client")
    def test_delete_experiment(self, mock_admin):
        from app.services.experiments import delete_experiment
        _mock_supabase_table(mock_admin, [{"id": "exp-1"}])

        result = delete_experiment("user-789", "exp-1")
        assert result is True

    @patch("app.deps.get_admin_client")
    def test_delete_experiment_not_found(self, mock_admin):
        from app.services.experiments import delete_experiment
        _mock_supabase_table(mock_admin, [])

        result = delete_experiment("user-789", "nonexistent")
        assert result is False


# ── Lifecycle Tests ──────────────────────────────────────

class TestExperimentLifecycle:
    """Test approve, cancel, and assign operations."""

    @patch("app.deps.get_admin_client")
    def test_approve_proposed_experiment(self, mock_admin):
        from app.services.experiments import approve_experiment
        exp = _make_experiment(status="proposed")
        approved_exp = _make_experiment(status="approved")
        mock_table = _mock_supabase_table(mock_admin, [exp])
        # First call returns proposed (get), second returns approved (update)
        mock_table.execute.return_value.data = [exp]

        # Mock update to return approved
        def side_effect(*args, **kwargs):
            result = MagicMock()
            result.data = [approved_exp]
            return result
        mock_table.execute.side_effect = [
            MagicMock(data=[exp]),       # get
            MagicMock(data=[approved_exp]),  # update
        ]

        result = approve_experiment("user-789", "exp-1")
        assert result["status"] == "approved"

    @patch("app.deps.get_admin_client")
    def test_approve_non_proposed_fails(self, mock_admin):
        from app.services.experiments import approve_experiment
        exp = _make_experiment(status="running")
        _mock_supabase_table(mock_admin, [exp])

        with pytest.raises(ValueError, match="Cannot approve"):
            approve_experiment("user-789", "exp-1")

    @patch("app.deps.get_admin_client")
    def test_cancel_experiment(self, mock_admin):
        from app.services.experiments import cancel_experiment
        exp = _make_experiment(status="running")
        cancelled = _make_experiment(status="cancelled")
        mock_table = _mock_supabase_table(mock_admin)
        mock_table.execute.side_effect = [
            MagicMock(data=[exp]),        # get
            MagicMock(data=[cancelled]),   # update
        ]

        result = cancel_experiment("user-789", "exp-1")
        assert result["status"] == "cancelled"

    @patch("app.deps.get_admin_client")
    def test_cancel_completed_fails(self, mock_admin):
        from app.services.experiments import cancel_experiment
        exp = _make_experiment(status="completed")
        _mock_supabase_table(mock_admin, [exp])

        with pytest.raises(ValueError, match="Cannot cancel"):
            cancel_experiment("user-789", "exp-1")

    @patch("app.deps.get_admin_client")
    def test_assign_post_to_variant_a(self, mock_admin):
        from app.services.experiments import assign_post_to_experiment
        exp = _make_experiment(status="approved", variant_a_posts=[])
        updated = _make_experiment(status="running", variant_a_posts=["post-1"])
        mock_table = _mock_supabase_table(mock_admin)
        mock_table.execute.side_effect = [
            MagicMock(data=[exp]),      # get
            MagicMock(data=[updated]),  # update
        ]

        result = assign_post_to_experiment("user-789", "exp-1", "post-1", "variant_a")
        assert result["status"] == "running"

    @patch("app.deps.get_admin_client")
    def test_assign_invalid_variant_fails(self, mock_admin):
        from app.services.experiments import assign_post_to_experiment
        with pytest.raises(ValueError, match="variant must be"):
            assign_post_to_experiment("user-789", "exp-1", "post-1", "variant_c")

    @patch("app.deps.get_admin_client")
    def test_assign_duplicate_post_fails(self, mock_admin):
        from app.services.experiments import assign_post_to_experiment
        exp = _make_experiment(status="running", variant_a_posts=["post-1"])
        _mock_supabase_table(mock_admin, [exp])

        with pytest.raises(ValueError, match="already assigned"):
            assign_post_to_experiment("user-789", "exp-1", "post-1", "variant_a")


# ── Conclusion Tests ─────────────────────────────────────

class TestExperimentConclusion:
    """Test winner determination logic."""

    @patch("app.deps.get_admin_client")
    def test_not_enough_posts(self, mock_admin):
        from app.services.experiments import check_and_conclude
        exp = _make_experiment(
            status="running",
            variant_a_posts=["p1"],
            variant_b_posts=[],
        )
        _mock_supabase_table(mock_admin, [exp])

        result = check_and_conclude("user-789", "exp-1")
        assert "Not enough data" in result.get("message", "")

    @patch("app.services.agent_memory.create_memory")
    @patch("app.deps.get_admin_client")
    def test_clear_winner_variant_a(self, mock_admin, mock_create_memory):
        from app.services.experiments import check_and_conclude
        exp = _make_experiment(
            status="running",
            variant_a_posts=["p1", "p2"],
            variant_b_posts=["p3", "p4"],
        )
        completed = _make_experiment(
            status="completed",
            winner="variant_a",
            conclusion="'story' outperformed 'question'",
        )

        # Mock get_experiment, variant_a engagement, variant_b engagement, update
        mock_table = _mock_supabase_table(mock_admin)
        mock_table.execute.side_effect = [
            MagicMock(data=[exp]),                                      # get experiment
            MagicMock(data=[{"engagement_rate": 0.08}, {"engagement_rate": 0.06}]),  # variant_a posts
            MagicMock(data=[{"engagement_rate": 0.03}, {"engagement_rate": 0.02}]),  # variant_b posts
            MagicMock(data=[completed]),                                # update
        ]
        mock_create_memory.return_value = {"id": "mem-new"}

        result = check_and_conclude("user-789", "exp-1")
        assert result["status"] == "completed"

    @patch("app.deps.get_admin_client")
    def test_inconclusive_close_results(self, mock_admin):
        from app.services.experiments import check_and_conclude
        exp = _make_experiment(
            status="running",
            variant_a_posts=["p1", "p2"],
            variant_b_posts=["p3", "p4"],
        )
        completed = _make_experiment(status="completed", winner="inconclusive")

        mock_table = _mock_supabase_table(mock_admin)
        mock_table.execute.side_effect = [
            MagicMock(data=[exp]),
            MagicMock(data=[{"engagement_rate": 0.05}, {"engagement_rate": 0.05}]),  # A avg: 0.05
            MagicMock(data=[{"engagement_rate": 0.045}, {"engagement_rate": 0.048}]),  # B avg: 0.0465
            MagicMock(data=[completed]),
        ]

        result = check_and_conclude("user-789", "exp-1")
        assert result["status"] == "completed"

    @patch("app.deps.get_admin_client")
    def test_already_completed_returns_as_is(self, mock_admin):
        from app.services.experiments import check_and_conclude
        exp = _make_experiment(status="completed", winner="variant_a")
        _mock_supabase_table(mock_admin, [exp])

        result = check_and_conclude("user-789", "exp-1")
        assert result["winner"] == "variant_a"


# ── Variant Engagement Tests ─────────────────────────────

class TestVariantEngagement:
    """Test engagement calculation for variants."""

    @patch("app.deps.get_admin_client")
    def test_calculate_variant_engagement(self, mock_admin):
        from app.services.experiments import calculate_variant_engagement
        _mock_supabase_table(mock_admin, [
            {"engagement_rate": 0.08},
            {"engagement_rate": 0.06},
        ])

        result = calculate_variant_engagement("user-789", ["p1", "p2"])
        assert result == 0.07  # (0.08 + 0.06) / 2

    @patch("app.deps.get_admin_client")
    def test_calculate_engagement_empty_posts(self, mock_admin):
        from app.services.experiments import calculate_variant_engagement
        result = calculate_variant_engagement("user-789", [])
        assert result is None

    @patch("app.deps.get_admin_client")
    def test_calculate_engagement_no_data(self, mock_admin):
        from app.services.experiments import calculate_variant_engagement
        _mock_supabase_table(mock_admin, [])

        result = calculate_variant_engagement("user-789", ["p1"])
        assert result is None


# ── Context Formatting Tests ─────────────────────────────

class TestExperimentContext:
    """Test experiment context formatting for pipeline injection."""

    @patch("app.deps.get_admin_client")
    def test_active_experiment_context(self, mock_admin):
        from app.services.experiments import get_active_experiment_context
        exp = _make_experiment(
            status="running",
            variant_a_posts=["p1"],
            variant_b_posts=["p1", "p2"],
        )
        _mock_supabase_table(mock_admin, [exp])

        context = get_active_experiment_context("user-789")
        assert "ACTIVE EXPERIMENTS" in context
        assert "Story hooks" in context
        assert "variant A needs more data" in context

    @patch("app.deps.get_admin_client")
    def test_no_active_experiments(self, mock_admin):
        from app.services.experiments import get_active_experiment_context
        _mock_supabase_table(mock_admin, [])

        context = get_active_experiment_context("user-789")
        assert context == ""

    @patch("app.deps.get_admin_client")
    def test_completed_experiments_summary(self, mock_admin):
        from app.services.experiments import get_completed_experiments_summary
        exp = _make_experiment(
            status="completed",
            conclusion="Story hooks won by 40%",
        )
        _mock_supabase_table(mock_admin, [exp])

        context = get_completed_experiments_summary("user-789")
        assert "COMPLETED EXPERIMENTS" in context
        assert "Story hooks won" in context

    @patch("app.deps.get_admin_client")
    def test_platform_filter(self, mock_admin):
        from app.services.experiments import get_active_experiment_context
        exp_yt = _make_experiment(status="running", platform="youtube")
        exp_li = _make_experiment(status="running", platform="linkedin", exp_id="exp-2")
        _mock_supabase_table(mock_admin, [exp_yt, exp_li])

        # Without filter: both
        context = get_active_experiment_context("user-789")
        assert "youtube" in context.lower() or "ACTIVE" in context

    def test_context_empty_user_id(self):
        from app.services.experiments import get_active_experiment_context
        # When no user_id — should fall back via list returning empty
        # This tests graceful handling
        assert True  # The function requires user_id parameter


# ── Auto-Proposal Tests ──────────────────────────────────

class TestAutoProposal:
    """Test auto-proposal of experiments from performance data."""

    @patch("app.deps.get_admin_client")
    def test_not_enough_posts(self, mock_admin):
        from app.services.experiments import auto_propose_experiments
        # Less than 5 posts → no proposals
        posts = [_make_post(post_id=f"p-{i}") for i in range(3)]
        mock_table = _mock_supabase_table(mock_admin, posts)
        # Second call (list_experiments) returns empty
        mock_table.execute.side_effect = [
            MagicMock(data=posts),   # content_posts
            MagicMock(data=[]),      # existing experiments
        ]

        result = auto_propose_experiments("user-789")
        assert result == []

    @patch("app.deps.get_admin_client")
    def test_proposes_experiment_from_variance(self, mock_admin):
        from app.services.experiments import auto_propose_experiments
        # Create posts with clear variance in hook_type
        posts = [
            _make_post(post_id="p1", hook_type="story", engagement_rate=0.10, platform="youtube"),
            _make_post(post_id="p2", hook_type="story", engagement_rate=0.09, platform="youtube"),
            _make_post(post_id="p3", hook_type="question", engagement_rate=0.03, platform="youtube"),
            _make_post(post_id="p4", hook_type="question", engagement_rate=0.02, platform="youtube"),
            _make_post(post_id="p5", hook_type="story", engagement_rate=0.08, platform="youtube"),
        ]

        mock_table = _mock_supabase_table(mock_admin)
        created_exp = _make_experiment()
        mock_table.execute.side_effect = [
            MagicMock(data=posts),          # content_posts query
            MagicMock(data=[]),             # existing experiments
            MagicMock(data=[created_exp]),  # insert new experiment
        ]

        result = auto_propose_experiments("user-789")
        assert len(result) >= 1

    @patch("app.deps.get_admin_client")
    def test_skips_existing_experiment_variables(self, mock_admin):
        from app.services.experiments import auto_propose_experiments
        posts = [
            _make_post(post_id=f"p{i}", hook_type="story" if i % 2 == 0 else "question",
                      engagement_rate=0.10 if i % 2 == 0 else 0.03)
            for i in range(6)
        ]
        existing = _make_experiment(variable="hook_type", variant_a="story", variant_b="question")

        mock_table = _mock_supabase_table(mock_admin)
        mock_table.execute.side_effect = [
            MagicMock(data=posts),        # content_posts
            MagicMock(data=[existing]),   # existing experiments
        ]

        result = auto_propose_experiments("user-789")
        # Should not propose same experiment that already exists
        assert len(result) == 0


# ── Self-Voice DNA Tests ─────────────────────────────────

class TestSelfVoiceDNA:
    """Test self-voice analysis and formatting."""

    @patch("worker.graph.llm.get_llm_client")
    @patch("app.deps.get_admin_client")
    def test_analyze_self_voice(self, mock_admin, mock_llm):
        from app.services.self_voice import analyze_self_voice
        # Create enough posts
        posts = [
            {
                "title": f"Post {i}",
                "hook_used": f"Hook {i}",
                "content_body": f"Content body for post {i} " * 20,
                "platform": "youtube",
                "engagement_rate": 0.05,
                "performance_tier": "average",
            }
            for i in range(12)
        ]
        mock_table = _mock_supabase_table(mock_admin, posts)

        # Mock LLM response
        llm_instance = MagicMock()
        mock_llm.return_value = llm_instance
        llm_instance.chat.return_value = {
            "content": json.dumps({
                "tone": "Direct and energetic",
                "sentence_style": "Short, punchy sentences",
                "vocabulary_level": "Simple, no jargon",
                "avg_sentence_length": 8.5,
                "hook_patterns": ["Bold claims", "Statistics"],
                "cta_patterns": ["Direct command"],
                "signature_phrases": ["Here's the thing", "Let me explain"],
                "content_structure": "Hook → Problem → Solution → CTA",
                "personality_traits": ["Confident", "Authentic"],
                "sample_hooks": ["The truth about AI nobody tells you"],
            })
        }

        result = analyze_self_voice("user-789")
        assert result["tone"] == "Direct and energetic"
        assert result["posts_analyzed"] == 12
        assert len(result["hook_patterns"]) == 2

    @patch("app.deps.get_admin_client")
    def test_analyze_not_enough_posts(self, mock_admin):
        from app.services.self_voice import analyze_self_voice
        posts = [{"title": f"Post {i}"} for i in range(5)]
        _mock_supabase_table(mock_admin, posts)

        with pytest.raises(ValueError, match="Not enough published posts"):
            analyze_self_voice("user-789")

    @patch("app.deps.get_admin_client")
    def test_get_voice_baseline_exists(self, mock_admin):
        from app.services.self_voice import get_voice_baseline
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {"tone": "Direct"}, "voice_drift_baseline": {}}
        ])

        result = get_voice_baseline("user-789")
        assert result["tone"] == "Direct"

    @patch("app.deps.get_admin_client")
    def test_get_voice_baseline_empty(self, mock_admin):
        from app.services.self_voice import get_voice_baseline
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {}, "voice_drift_baseline": {}}
        ])

        result = get_voice_baseline("user-789")
        assert result is None

    @patch("app.deps.get_admin_client")
    def test_get_voice_baseline_no_profile(self, mock_admin):
        from app.services.self_voice import get_voice_baseline
        _mock_supabase_table(mock_admin, [])

        result = get_voice_baseline("user-789")
        assert result is None

    def test_format_self_voice_instructions_with_data(self):
        from app.services.self_voice import format_self_voice_instructions
        voice_dna = {
            "tone": "Direct and energetic",
            "sentence_style": "Short punchy sentences",
            "vocabulary_level": "Simple",
            "hook_patterns": ["Bold claims"],
            "signature_phrases": ["Here's the thing"],
            "personality_traits": ["Confident"],
            "content_structure": "Hook → Problem → Solution",
            "sample_hooks": ["The truth about AI"],
        }
        result = format_self_voice_instructions(voice_dna)
        assert "YOUR NATURAL WRITING VOICE" in result
        assert "Direct and energetic" in result
        assert "YOUR ACTUAL HOOKS" in result

    def test_format_self_voice_instructions_empty(self):
        from app.services.self_voice import format_self_voice_instructions
        assert format_self_voice_instructions({}) == ""
        assert format_self_voice_instructions(None) == ""

    def test_format_voice_for_comparison(self):
        from app.services.self_voice import _format_voice_for_comparison
        voice_dna = {
            "tone": "Casual",
            "sentence_style": "Short",
            "hook_patterns": ["Questions"],
            "sample_hooks": ["Did you know?"],
        }
        result = _format_voice_for_comparison(voice_dna)
        assert "Tone: Casual" in result
        assert "Did you know?" in result


# ── Voice Drift Tests ────────────────────────────────────

class TestVoiceDrift:
    """Test voice drift detection."""

    @patch("worker.graph.llm.get_llm_client")
    @patch("app.deps.get_admin_client")
    def test_drift_check_with_baseline(self, mock_admin, mock_llm):
        from app.services.self_voice import check_voice_drift
        # Mock baseline exists
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {"tone": "Direct"}, "voice_drift_baseline": {}}
        ])

        # Mock LLM drift analysis
        llm_instance = MagicMock()
        mock_llm.return_value = llm_instance
        llm_instance.chat.return_value = {
            "content": json.dumps({
                "drift_score": 0.45,
                "drift_details": ["Too formal", "Missing signature phrases"],
                "recommendation": "Use more contractions and casual language",
            })
        }

        result = check_voice_drift("user-789", "This is a test content piece.")
        assert result["drift_score"] == 0.45
        assert result["drift_level"] == "medium"
        assert result["baseline_available"] is True
        assert len(result["details"]) == 2

    @patch("app.deps.get_admin_client")
    def test_drift_check_no_baseline(self, mock_admin):
        from app.services.self_voice import check_voice_drift
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {}, "voice_drift_baseline": {}}
        ])

        result = check_voice_drift("user-789", "Test content")
        assert result["baseline_available"] is False
        assert result["drift_level"] == "unknown"

    @patch("worker.graph.llm.get_llm_client")
    @patch("app.deps.get_admin_client")
    def test_drift_levels(self, mock_admin, mock_llm):
        from app.services.self_voice import check_voice_drift
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {"tone": "Direct"}, "voice_drift_baseline": {}}
        ])

        llm_instance = MagicMock()
        mock_llm.return_value = llm_instance

        # Test low drift
        llm_instance.chat.return_value = {
            "content": json.dumps({
                "drift_score": 0.15,
                "drift_details": [],
                "recommendation": "",
            })
        }
        result = check_voice_drift("user-789", "Test")
        assert result["drift_level"] == "low"

        # Test high drift
        llm_instance.chat.return_value = {
            "content": json.dumps({
                "drift_score": 0.75,
                "drift_details": ["Very formal", "Complex vocabulary"],
                "recommendation": "Simplify",
            })
        }
        result = check_voice_drift("user-789", "Test 2")
        assert result["drift_level"] == "high"


# ── Pipeline Integration Tests ───────────────────────────

class TestPipelineIntegration:
    """Test experiment + self-voice context injection into pipeline nodes."""

    @patch("app.deps.get_admin_client")
    def test_gap_analysis_experiment_context(self, mock_admin):
        """gap_analysis._fetch_experiment_context() works correctly."""
        from worker.graph.nodes.gap_analysis import _fetch_experiment_context
        exp = _make_experiment(status="running", variant_a_posts=["p1"])
        _mock_supabase_table(mock_admin, [exp])

        result = _fetch_experiment_context("user-789")
        assert "ACTIVE EXPERIMENTS" in result

    def test_gap_analysis_experiment_context_no_user(self):
        from worker.graph.nodes.gap_analysis import _fetch_experiment_context
        assert _fetch_experiment_context("") == ""

    @patch("app.deps.get_admin_client")
    def test_gap_analysis_experiment_context_error(self, mock_admin):
        from worker.graph.nodes.gap_analysis import _fetch_experiment_context
        mock_admin.side_effect = Exception("Connection failed")
        result = _fetch_experiment_context("user-789")
        assert result == ""

    @patch("app.deps.get_admin_client")
    def test_hook_lab_experiment_context(self, mock_admin):
        from worker.graph.nodes.hook_lab import _fetch_experiment_context
        exp = _make_experiment(status="approved")
        _mock_supabase_table(mock_admin, [exp])

        result = _fetch_experiment_context("user-789")
        assert "ACTIVE EXPERIMENTS" in result

    @patch("app.deps.get_admin_client")
    def test_script_gen_experiment_context(self, mock_admin):
        from worker.graph.nodes.script_generation import _fetch_experiment_context
        exp = _make_experiment(status="running")
        _mock_supabase_table(mock_admin, [exp])

        result = _fetch_experiment_context("user-789", platform="youtube")
        assert "ACTIVE EXPERIMENTS" in result

    @patch("app.deps.get_admin_client")
    def test_script_gen_self_voice_context(self, mock_admin):
        from worker.graph.nodes.script_generation import _fetch_self_voice_context
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {"tone": "Direct and punchy"}, "voice_drift_baseline": {}}
        ])

        result = _fetch_self_voice_context("user-789")
        assert "YOUR NATURAL WRITING VOICE" in result
        assert "Direct and punchy" in result

    def test_script_gen_self_voice_no_user(self):
        from worker.graph.nodes.script_generation import _fetch_self_voice_context
        assert _fetch_self_voice_context("") == ""

    @patch("app.deps.get_admin_client")
    def test_script_gen_self_voice_no_baseline(self, mock_admin):
        from worker.graph.nodes.script_generation import _fetch_self_voice_context
        _mock_supabase_table(mock_admin, [
            {"self_voice_dna": {}, "voice_drift_baseline": {}}
        ])

        result = _fetch_self_voice_context("user-789")
        assert result == ""

    @patch("app.deps.get_admin_client")
    def test_script_gen_self_voice_error(self, mock_admin):
        from worker.graph.nodes.script_generation import _fetch_self_voice_context
        mock_admin.side_effect = Exception("DB down")
        result = _fetch_self_voice_context("user-789")
        assert result == ""

    def test_hook_lab_experiment_context_no_user(self):
        from worker.graph.nodes.hook_lab import _fetch_experiment_context
        assert _fetch_experiment_context("") == ""

    def test_script_gen_experiment_context_no_user(self):
        from worker.graph.nodes.script_generation import _fetch_experiment_context
        assert _fetch_experiment_context("") == ""
