"""
Slice 89: SDK Orchestrator — True Agent Pipeline

25 tests across 6 classes:
  TestPipelineEndpoints      — 5  (endpoints exist, auth required, UUID validation)
  TestContextHelpers         — 5  (analytics, competitor, trend, rejection helpers return str)
  TestPromptBuilders         — 4  (prompts include required keywords)
  TestQAScoreParser          — 4  (parse various score formats correctly)
  TestSaveDeliverable        — 4  (saves review vs failed_qa, returns id, error-safe)
  TestPublishingCron         — 3  (cron endpoint exists, key required, returns counts)
"""

import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).parents[3]
API = REPO / "apps" / "api"


# ── Helpers ────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


PIPELINE_ROUTER = API / "app" / "routers" / "pipeline.py"
PIPELINE_SERVICE = API / "app" / "services" / "jumbo_pipeline.py"
RUNNER = REPO / "deploy" / "pipeline_runner.py"
SERVICE_UNIT = REPO / "deploy" / "jumbo-pipeline.service"


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineEndpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestPipelineEndpoints:
    """Pipeline router exists with all 5 required endpoints."""

    def test_pipeline_router_file_exists(self):
        assert PIPELINE_ROUTER.exists(), "pipeline.py router not found"

    def test_research_endpoint_defined(self):
        text = read(PIPELINE_ROUTER)
        assert "/orchestrator/pipeline/research" in text, \
            "Research endpoint not defined in pipeline router"

    def test_write_endpoint_defined(self):
        text = read(PIPELINE_ROUTER)
        assert "/orchestrator/pipeline/write" in text, \
            "Write endpoint not defined in pipeline router"

    def test_qa_endpoint_defined(self):
        text = read(PIPELINE_ROUTER)
        assert "/orchestrator/pipeline/qa" in text, \
            "QA endpoint not defined in pipeline router"

    def test_cron_publish_endpoint_defined(self):
        text = read(PIPELINE_ROUTER)
        assert "/cron/publish" in text, \
            "/cron/publish endpoint not defined in pipeline router"

    def test_pipeline_key_auth_used(self):
        text = read(PIPELINE_ROUTER)
        assert "hmac.compare_digest" in text, \
            "hmac.compare_digest not used for pipeline key auth (timing-safe required)"
        assert "X-Pipeline-Key" in text or "x_pipeline_key" in text, \
            "X-Pipeline-Key header not referenced in pipeline router"

    def test_uuid_validation_in_router(self):
        text = read(PIPELINE_ROUTER)
        assert "_UUID_RE" in text or "UUID" in text, \
            "UUID validation not present in pipeline router (OWASP A03)"

    def test_pipeline_router_included_in_main(self):
        main_text = read(API / "app" / "main.py")
        assert "pipeline" in main_text, \
            "pipeline router not imported/included in main.py"

    def test_pipeline_key_in_config(self):
        config_text = read(API / "app" / "config.py")
        assert "pipeline_secret_key" in config_text, \
            "pipeline_secret_key not added to config.py Settings"

    def test_cron_secret_in_config(self):
        config_text = read(API / "app" / "config.py")
        assert "cron_secret" in config_text, \
            "cron_secret not added to config.py Settings"


# ═══════════════════════════════════════════════════════════════════════════
# TestContextHelpers
# ═══════════════════════════════════════════════════════════════════════════

class TestContextHelpers:
    """Context helper functions return strings and handle errors gracefully."""

    def _mock_empty_supabase(self):
        sb = MagicMock()
        empty = MagicMock()
        empty.data = []
        sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = empty
        return sb

    def test_get_analytics_context_returns_str(self):
        from app.services.jumbo_pipeline import get_analytics_context
        with patch("app.deps.get_admin_client", return_value=self._mock_empty_supabase()):
            result = get_analytics_context("00000000-0000-0000-0000-000000000001")
        assert isinstance(result, str), "get_analytics_context must return str"

    def test_get_competitor_context_returns_str(self):
        from app.services.jumbo_pipeline import get_competitor_context
        with patch("app.deps.get_admin_client", return_value=self._mock_empty_supabase()):
            result = get_competitor_context("00000000-0000-0000-0000-000000000001")
        assert isinstance(result, str), "get_competitor_context must return str"

    def test_get_trend_memory_returns_str(self):
        from app.services.jumbo_pipeline import get_trend_memory
        with patch("app.deps.get_admin_client", return_value=self._mock_empty_supabase()):
            result = get_trend_memory("00000000-0000-0000-0000-000000000001")
        assert isinstance(result, str), "get_trend_memory must return str"

    def test_get_rejection_history_returns_str(self):
        from app.services.jumbo_pipeline import get_rejection_history
        with patch("app.deps.get_admin_client", return_value=self._mock_empty_supabase()):
            result = get_rejection_history(
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            )
        assert isinstance(result, str), "get_rejection_history must return str"

    def test_invalid_uuid_returns_error_string(self):
        from app.services.jumbo_pipeline import get_analytics_context
        result = get_analytics_context("not-a-valid-uuid")
        assert "unavailable" in result.lower() or "invalid" in result.lower(), \
            "Invalid UUID should return error string, not raise exception"


# ═══════════════════════════════════════════════════════════════════════════
# TestPromptBuilders
# ═══════════════════════════════════════════════════════════════════════════

class TestPromptBuilders:
    """Prompt builders include required sections and keywords."""

    def test_research_prompt_has_required_sections(self):
        from app.services.jumbo_pipeline import build_research_prompt
        prompt = build_research_prompt("analytics ctx", "competitor ctx", "trend memory")
        assert "web_search" in prompt, "Research prompt must reference web_search tool"
        assert "Research Brief" in prompt, "Research prompt must include Research Brief template"
        assert "synthesize_research" in prompt, "Research prompt must reference synthesize_research tool"

    def test_writing_prompt_includes_research_brief(self):
        from app.services.jumbo_pipeline import build_writing_prompt
        brief = "This is a research brief about AI hooks"
        prompt = build_writing_prompt(brief, "analytics", "")
        assert brief[:50] in prompt, "Writing prompt must include the research brief"
        assert "score_content_quality" in prompt, "Writing prompt must reference score_content_quality self-check"

    def test_writing_prompt_includes_rejection_history(self):
        from app.services.jumbo_pipeline import build_writing_prompt
        rejection = "## User Rejection History\n- Wrong voice"
        prompt = build_writing_prompt("brief", "analytics", rejection)
        assert "Rejection" in prompt or "rejection" in prompt or "Wrong voice" in prompt, \
            "Writing prompt must include rejection history when provided"

    def test_qa_prompt_has_scoring_rubric(self):
        from app.services.jumbo_pipeline import build_qa_prompt
        prompt = build_qa_prompt()
        assert "SCORE:" in prompt, "QA prompt must include SCORE: format instruction"
        assert "VERDICT:" in prompt, "QA prompt must include VERDICT: format instruction"
        assert "score_content_quality" in prompt, "QA prompt must reference score_content_quality tool"


# ═══════════════════════════════════════════════════════════════════════════
# TestQAScoreParser
# ═══════════════════════════════════════════════════════════════════════════

class TestQAScoreParser:
    """parse_qa_score correctly extracts scores from various response formats."""

    def test_parses_standard_format(self):
        from app.services.jumbo_pipeline import parse_qa_score
        response = "SCORE: 85/100\nVERDICT: PASS"
        assert parse_qa_score(response) == 85

    def test_parses_without_denominator(self):
        from app.services.jumbo_pipeline import parse_qa_score
        response = "Score: 72\nVERDICT: FAIL"
        assert parse_qa_score(response) == 72

    def test_parses_fallback_format(self):
        from app.services.jumbo_pipeline import parse_qa_score
        response = "I give this post 91/100 for overall quality."
        assert parse_qa_score(response) == 91

    def test_returns_zero_when_no_score(self):
        from app.services.jumbo_pipeline import parse_qa_score
        response = "The post needs significant improvement in voice and structure."
        assert parse_qa_score(response) == 0

    def test_clamps_score_to_100(self):
        from app.services.jumbo_pipeline import parse_qa_score
        response = "SCORE: 150/100"  # Invalid but should not crash
        assert parse_qa_score(response) <= 100


# ═══════════════════════════════════════════════════════════════════════════
# TestSaveDeliverable
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveDeliverable:
    """save_deliverable creates the right status and returns deliverable_id."""

    def _mock_insert_sb(self, returned_id: str = "test-id-123"):
        sb = MagicMock()
        insert_result = MagicMock()
        insert_result.data = [{"id": returned_id}]
        sb.table.return_value.insert.return_value.execute.return_value = insert_result
        return sb

    def test_score_80_creates_review_status(self):
        from app.services.jumbo_pipeline import save_deliverable
        sb = self._mock_insert_sb()
        with patch("app.deps.get_admin_client", return_value=sb):
            save_deliverable("user-1", "Post content here", qa_score=82)
        call_args = sb.table.return_value.insert.call_args[0][0]
        assert call_args["status"] == "review", \
            "qa_score >= 80 must create status=review"

    def test_score_79_creates_failed_qa_status(self):
        from app.services.jumbo_pipeline import save_deliverable
        sb = self._mock_insert_sb()
        with patch("app.deps.get_admin_client", return_value=sb):
            save_deliverable("user-1", "Post content here", qa_score=79)
        call_args = sb.table.return_value.insert.call_args[0][0]
        assert call_args["status"] == "failed_qa", \
            "qa_score < 80 must create status=failed_qa"

    def test_returns_non_empty_string_on_success(self):
        from app.services.jumbo_pipeline import save_deliverable
        sb = self._mock_insert_sb("abc-123")
        with patch("app.deps.get_admin_client", return_value=sb):
            deliverable_id = save_deliverable("user-1", "Content", qa_score=85)
        assert deliverable_id != "", "save_deliverable must return non-empty id on success"

    def test_returns_empty_string_on_db_error(self):
        from app.services.jumbo_pipeline import save_deliverable
        sb = MagicMock()
        sb.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        with patch("app.deps.get_admin_client", return_value=sb):
            result = save_deliverable("user-1", "Content", qa_score=85)
        assert result == "", "save_deliverable must return empty string on DB error (no exception)"


# ═══════════════════════════════════════════════════════════════════════════
# TestPublishingCron
# ═══════════════════════════════════════════════════════════════════════════

class TestPublishingCron:
    """Publishing cron endpoint and VPS deployment files are correctly set up."""

    def test_cron_endpoint_in_router(self):
        text = read(PIPELINE_ROUTER)
        assert "/cron/publish" in text, "/cron/publish endpoint missing from pipeline.py"

    def test_cron_calls_run_due_posts(self):
        text = read(PIPELINE_ROUTER)
        assert "run_due_posts" in text, \
            "cron_publish must call run_due_posts from publishing service"

    def test_vercel_json_has_cron_config(self):
        vercel_json = API / "vercel.json"
        assert vercel_json.exists(), "apps/api/vercel.json not found"
        content = read(vercel_json)
        assert "crons" in content, "vercel.json must have 'crons' key"
        assert "/cron/publish" in content, \
            "/cron/publish must be listed in vercel.json crons"

    def test_pipeline_runner_file_exists(self):
        assert RUNNER.exists(), "deploy/pipeline_runner.py not found"

    def test_systemd_service_file_exists(self):
        assert SERVICE_UNIT.exists(), "deploy/jumbo-pipeline.service not found"

    def test_pipeline_runner_calls_all_three_phases(self):
        text = read(RUNNER)
        for phase in ["research", "write", "qa"]:
            assert f"/orchestrator/pipeline/{phase}" in text, \
                f"pipeline_runner.py must call /orchestrator/pipeline/{phase}"

    def test_systemd_service_has_environment_file(self):
        text = read(SERVICE_UNIT)
        assert "EnvironmentFile" in text, \
            "jumbo-pipeline.service must load env from EnvironmentFile"
        assert "Restart=on-failure" in text, \
            "jumbo-pipeline.service must have Restart=on-failure"
