"""Tests for OAuth, export, worker hardening, model routing, and log redaction.

Verifies:
  - OAuth status/disconnect endpoints return correct structure
  - Google Docs + Notion export endpoints enforce OAuth connection
  - Workflow abandon endpoint
  - Worker queue stale recovery logic
  - Per-workflow budget check
  - Model routing per pipeline step
  - Log redaction of sensitive query params
  - Google Docs + Notion content formatting
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app


# ── Fixtures ──────────────────────────────────────────


class FakeUser:
    id = "test-oauth-user-123"
    email = "test-oauth@example.com"


@pytest.fixture(autouse=True)
def _auth_override():
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


# ── OAuth Status Tests ────────────────────────────────


class TestOAuthGoogleStatus:
    """Test Google OAuth status endpoint."""

    @patch("app.routers.oauth.get_admin_client")
    def test_not_connected(self, mock_admin):
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_admin.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp
        resp = client.get("/oauth/google/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False
        assert body["provider"] == "google"

    @patch("app.routers.oauth.get_admin_client")
    def test_connected(self, mock_admin):
        mock_resp = MagicMock()
        mock_resp.data = [{"scopes": ["drive.file"], "metadata": {}}]
        mock_admin.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp
        resp = client.get("/oauth/google/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["provider"] == "google"


class TestOAuthNotionStatus:
    """Test Notion OAuth status endpoint."""

    @patch("app.routers.oauth.get_admin_client")
    def test_not_connected(self, mock_admin):
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_admin.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp
        resp = client.get("/oauth/notion/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False
        assert body["provider"] == "notion"


class TestOAuthDisconnect:
    """Test disconnect endpoints."""

    @patch("app.routers.oauth.get_admin_client")
    def test_google_disconnect(self, mock_admin):
        mock_admin.return_value.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        resp = client.delete("/oauth/google/disconnect")
        assert resp.status_code == 200
        assert "disconnected" in resp.json()["message"].lower()
        assert resp.json()["provider"] == "google"

    @patch("app.routers.oauth.get_admin_client")
    def test_notion_disconnect(self, mock_admin):
        mock_admin.return_value.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        resp = client.delete("/oauth/notion/disconnect")
        assert resp.status_code == 200
        assert "disconnected" in resp.json()["message"].lower()
        assert resp.json()["provider"] == "notion"


# ── Auth URL Not Configured Tests ─────────────────────


class TestOAuthAuthURLNotConfigured:
    """Test auth URL endpoints return 503 when OAuth is not configured."""

    @patch("app.routers.oauth.settings")
    def test_google_auth_url_not_configured(self, mock_settings):
        mock_settings.google_client_id = ""
        mock_settings.google_client_secret = ""
        resp = client.get("/oauth/google/auth-url")
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()

    @patch("app.routers.oauth.settings")
    def test_notion_auth_url_not_configured(self, mock_settings):
        mock_settings.notion_client_id = ""
        mock_settings.notion_client_secret = ""
        resp = client.get("/oauth/notion/auth-url")
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


# ── Export Enforcement Tests ──────────────────────────


class TestExportEnforcement:
    """Test that Google Docs / Notion export returns 403 without OAuth."""

    @patch("app.routers.workflows.get_admin_client")
    @patch("app.routers.oauth.get_admin_client")
    def test_google_docs_export_requires_connection(self, mock_oauth_admin, mock_wf_admin):
        # get_google_credentials queries oauth_tokens and finds nothing
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_oauth_admin.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp

        resp = client.post("/workflows/fake-id/export/google-docs")
        assert resp.status_code == 403
        assert "not connected" in resp.json()["detail"].lower()

    @patch("app.routers.workflows.get_admin_client")
    @patch("app.routers.oauth.get_admin_client")
    def test_notion_export_requires_connection(self, mock_oauth_admin, mock_wf_admin):
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_oauth_admin.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp

        resp = client.post("/workflows/fake-id/export/notion")
        assert resp.status_code == 403
        assert "not connected" in resp.json()["detail"].lower()


# ── Workflow Abandon Tests ────────────────────────────


class TestWorkflowAbandon:
    """Test the abandon workflow endpoint."""

    @patch("app.routers.workflows.get_admin_client")
    def test_abandon_active_workflow(self, mock_admin):
        # SELECT returns running workflow
        select_mock = MagicMock()
        select_mock.data = [{"id": "wf-1", "status": "running"}]
        # UPDATE succeeds
        update_mock = MagicMock()
        update_mock.data = [{"id": "wf-1"}]
        # INSERT (audit) succeeds
        insert_mock = MagicMock()
        insert_mock.data = [{}]

        table = MagicMock()
        mock_admin.return_value.table.return_value = table
        table.select.return_value.eq.return_value.eq.return_value.execute.return_value = select_mock
        table.update.return_value.eq.return_value.execute.return_value = update_mock
        table.insert.return_value.execute.return_value = insert_mock

        resp = client.post("/workflows/wf-1/abandon")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert "abandoned" in body["message"].lower()

    @patch("app.routers.workflows.get_admin_client")
    def test_abandon_terminal_workflow_rejected(self, mock_admin):
        table = MagicMock()
        mock_admin.return_value.table.return_value = table
        table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "wf-1", "status": "approved"}]
        )

        resp = client.post("/workflows/wf-1/abandon")
        assert resp.status_code == 409
        assert "terminal" in resp.json()["detail"].lower()

    @patch("app.routers.workflows.get_admin_client")
    def test_abandon_nonexistent_workflow(self, mock_admin):
        table = MagicMock()
        mock_admin.return_value.table.return_value = table
        table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        resp = client.post("/workflows/fake-id/abandon")
        assert resp.status_code == 404


# ── Worker Hardening Tests ────────────────────────────


class TestWorkerQueue:
    """Test worker queue features."""

    def test_max_retries_exceeded_moves_to_dlq(self):
        """Workflow with retry_count >= MAX_RETRIES should be failed and not claimed."""
        from worker.queue import MAX_RETRIES, claim_next_job

        mock_client = MagicMock()

        # _recover_stale_claims: nothing stale
        stale_resp = MagicMock()
        stale_resp.data = []

        # claim_next_job: workflow SELECT returns one with exhausted retries
        queued_resp = MagicMock()
        queued_resp.data = [{
            "id": "wf-dlq",
            "user_id": "user-1",
            "goal_text": "test",
            "settings": {},
            "current_step": None,
            "retry_count": MAX_RETRIES,
        }]

        # Set up chained returns:
        # First call to .table("workflows").select().eq("status","queued")... -> queued_resp
        # Second call to .table("workflows").select().eq("status","running")... -> stale_resp (nothing stale)
        # The order depends on _recover_stale_claims running first

        # Simplify: mock all table calls
        table_mock = MagicMock()
        mock_client.table.return_value = table_mock

        # For _recover_stale_claims: .select().eq().lt().limit().execute()
        table_mock.select.return_value.eq.return_value.lt.return_value.limit.return_value.execute.return_value = stale_resp

        # For claim_next_job main: .select().eq().order().limit().execute()
        table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = queued_resp

        # For the DLQ update: .update().eq().execute()
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        # For the audit insert: .insert().execute()
        table_mock.insert.return_value.execute.return_value = MagicMock(data=[])

        result = claim_next_job(mock_client)
        # Should return None because the workflow was moved to DLQ
        assert result is None

    def test_release_claim(self):
        """release_claim should clear claimed_at."""
        from worker.queue import release_claim

        mock_client = MagicMock()
        release_claim(mock_client, "wf-123")

        # Verify update was called
        mock_client.table.return_value.update.assert_called_once()
        call_args = mock_client.table.return_value.update.call_args[0][0]
        assert call_args["claimed_at"] is None


# ── Model Routing Tests ───────────────────────────────


class TestModelRouting:
    """Test model routing per pipeline step."""

    def test_creative_steps_use_gpt4o(self):
        from worker.graph.llm import get_model_for_step
        for step in ["signal_research", "gap_analysis", "topic_selection", "hook_lab", "script_generation"]:
            assert get_model_for_step(step) == "gpt-4o", f"Step {step} should use gpt-4o"

    def test_checking_steps_use_gpt4o_mini(self):
        from worker.graph.llm import get_model_for_step
        for step in ["editor", "testing", "approval"]:
            assert get_model_for_step(step) == "gpt-4o-mini", f"Step {step} should use gpt-4o-mini"

    def test_unknown_step_defaults_to_gpt4o(self):
        from worker.graph.llm import get_model_for_step
        assert get_model_for_step("unknown_step") == "gpt-4o"
        assert get_model_for_step("") == "gpt-4o"


# ── Per-Workflow Budget Tests ─────────────────────────


class TestWorkflowBudget:
    """Test per-workflow token budget enforcement."""

    def test_budget_exceeded_raises(self):
        from worker.graph.llm import (
            WorkflowBudgetExceeded,
            _check_workflow_budget,
            set_tracking_context,
            clear_tracking_context,
        )

        set_tracking_context("wf-budget", "user-1", "script_generation")
        try:
            with patch("worker.graph.llm.settings") as mock_settings:
                mock_settings.max_tokens_per_workflow = 1000  # Low ceiling

                with patch("app.deps.get_admin_client") as mock_admin:
                    mock_admin.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                        data=[
                            {"input_tokens": 600, "output_tokens": 500},
                        ]
                    )

                    with pytest.raises(WorkflowBudgetExceeded):
                        _check_workflow_budget()
        finally:
            clear_tracking_context()

    def test_budget_ok_does_not_raise(self):
        from worker.graph.llm import (
            _check_workflow_budget,
            set_tracking_context,
            clear_tracking_context,
        )

        set_tracking_context("wf-ok", "user-2", "editor")
        try:
            with patch("worker.graph.llm.settings") as mock_settings:
                mock_settings.max_tokens_per_workflow = 200000  # High ceiling

                with patch("app.deps.get_admin_client") as mock_admin:
                    mock_admin.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                        data=[
                            {"input_tokens": 100, "output_tokens": 50},
                        ]
                    )

                    # Should not raise
                    _check_workflow_budget()
        finally:
            clear_tracking_context()

    def test_no_tracking_context_skips_check(self):
        from worker.graph.llm import (
            _check_workflow_budget,
            clear_tracking_context,
        )

        clear_tracking_context()
        # Should not raise and should not call admin
        _check_workflow_budget()


# ── Log Redaction Tests ───────────────────────────────


class TestLogRedaction:
    """Test that sensitive query params are redacted in logged paths."""

    def test_redact_code(self):
        from app.main import _redact_query
        result = _redact_query("/oauth/google/callback?code=abc123&state=xyz")
        assert "abc123" not in result
        assert "xyz" not in result
        assert "code=***" in result
        assert "state=***" in result

    def test_preserves_safe_params(self):
        from app.main import _redact_query
        result = _redact_query("/workflows?status=running")
        assert result == "/workflows?status=running"

    def test_no_params_unchanged(self):
        from app.main import _redact_query
        result = _redact_query("/health")
        assert result == "/health"

    def test_redacts_token_params(self):
        from app.main import _redact_query
        result = _redact_query("/callback?access_token=secret&refresh_token=also_secret")
        assert "secret" not in result
        assert "also_secret" not in result
        assert "access_token=***" in result
        assert "refresh_token=***" in result


# ── Google Docs Service Tests ─────────────────────────


class TestGoogleDocsFormatting:
    """Test Google Docs content formatting."""

    def test_build_doc_requests_basic(self):
        from app.services.google_docs import _build_doc_requests

        pack = {
            "youtube_long": {
                "hook": "This is a hook",
                "sections": [
                    {"timestamp": "0:00", "heading": "Intro", "script": "Hello world"},
                ],
            },
            "titles": ["Title A", "Title B"],
        }

        sections = _build_doc_requests(pack, "Test goal")
        assert len(sections) > 0
        texts = [s["text"] for s in sections]
        full_text = "".join(texts)
        assert "YouTube Long-Form" in full_text
        assert "Title A" in full_text
        assert "This is a hook" in full_text

    def test_build_doc_requests_empty_pack(self):
        from app.services.google_docs import _build_doc_requests

        sections = _build_doc_requests({}, "")
        # Should have at least the title section
        assert len(sections) >= 1
        assert "Content Pack" in sections[0]["text"]

    def test_build_doc_requests_linkedin_twitter(self):
        from app.services.google_docs import _build_doc_requests

        pack = {
            "linkedin_posts": [
                {"post_type": "story", "hook_line": "Hook line", "body": "Body text", "cta": "Follow me"},
            ],
            "twitter_posts": [
                {"angle": "hot_take", "tweet_text": "This is spicy"},
            ],
        }

        sections = _build_doc_requests(pack, "Multi-platform")
        full_text = "".join(s["text"] for s in sections)
        assert "LinkedIn" in full_text
        assert "Twitter" in full_text
        assert "Hook line" in full_text
        assert "This is spicy" in full_text


# ── Notion Export Service Tests ───────────────────────


class TestNotionFormatting:
    """Test Notion content block building."""

    def test_build_notion_blocks_basic(self):
        from app.services.notion_export import _build_notion_blocks

        pack = {
            "linkedin_posts": [
                {"post_type": "story", "hook_line": "Here's what happened", "body": "A story...", "cta": "Follow me"},
            ],
            "twitter_posts": [
                {"angle": "hot_take", "tweet_text": "This is spicy"},
            ],
        }

        blocks = _build_notion_blocks(pack)
        assert len(blocks) > 0

        # Check heading blocks for LinkedIn and Twitter
        heading_texts = []
        for b in blocks:
            btype = b.get("type", "")
            if btype.startswith("heading_"):
                rich_text = b.get(btype, {}).get("rich_text", [])
                if rich_text:
                    heading_texts.append(rich_text[0].get("text", {}).get("content", ""))

        assert any("LinkedIn" in t for t in heading_texts)
        assert any("Twitter" in t for t in heading_texts)

    def test_build_notion_blocks_empty_pack(self):
        from app.services.notion_export import _build_notion_blocks
        blocks = _build_notion_blocks({})
        assert len(blocks) == 0

    def test_build_notion_blocks_long_text_chunked(self):
        """Text longer than 2000 chars should be chunked."""
        from app.services.notion_export import _text_block

        long_text = "x" * 5000
        block = _text_block(long_text)
        rich_text = block["paragraph"]["rich_text"]
        # 5000 chars / 2000 chunk = 3 chunks
        assert len(rich_text) == 3
        assert len(rich_text[0]["text"]["content"]) == 2000
        assert len(rich_text[2]["text"]["content"]) == 1000


# ── Cost Estimation Tests ─────────────────────────────


class TestCostEstimation:
    """Test the cost estimation function."""

    def test_gpt4o_cost(self):
        from worker.graph.llm import estimate_cost
        # 1000 input tokens at $0.0025/1K + 1000 output tokens at $0.01/1K
        cost = estimate_cost("gpt-4o", 1000, 1000)
        assert abs(cost - 0.0125) < 0.0001

    def test_gpt4o_mini_cost(self):
        from worker.graph.llm import estimate_cost
        # 1000 input tokens at $0.00015/1K + 1000 output tokens at $0.0006/1K
        cost = estimate_cost("gpt-4o-mini", 1000, 1000)
        assert abs(cost - 0.00075) < 0.0001

    def test_unknown_model_defaults_to_gpt4o(self):
        from worker.graph.llm import estimate_cost
        cost = estimate_cost("unknown-model", 1000, 1000)
        assert abs(cost - 0.0125) < 0.0001
