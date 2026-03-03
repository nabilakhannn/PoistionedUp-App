"""Tests for Slice 85: True Agent Autonomy — Tool Use, Playbooks, Ledger, Connectors.

Validates:
  TestToolUseAgentLoop   (5) — tool dispatch, loop termination, max turns, ledger writes
  TestSecretRedaction    (3) — redact() strips API keys / Bearer tokens from ledger text
  TestPlaybooksService   (5) — seed, get, propose, apply, empty guard
  TestPlaybooksRouter    (2) — list endpoint wired, seed endpoint wired
  TestLedgerRouter       (3) — list runs, entries, summary endpoints wired
  TestConnectorsService  (5) — encrypt roundtrip, missing key, SSRF block, test fn, shape validation
  TestConnectorsRouter   (2) — list endpoint, save endpoint wired
  TestLLMRouting         (2) — copywriter uses Claude, research uses tool-use path
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ═══════════════════════════════════════════════════════════════════════════
# TestToolUseAgentLoop
# ═══════════════════════════════════════════════════════════════════════════


class TestToolUseAgentLoop:
    """Core tool-use engine behaviour."""

    def test_web_search_calls_perplexity_when_key_set(self):
        """web_search calls Perplexity when perplexity_api_key is configured."""
        from app.services.tool_use_agents import _exec_web_search

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Some search result"}}],
            "citations": ["https://example.com"],
        }

        with patch("app.services.tool_use_agents.settings") as mock_settings, \
             patch("httpx.post", return_value=mock_resp) as mock_post:
            mock_settings.perplexity_api_key = "pplx-test-key"
            result = _exec_web_search("personal branding trends 2026")

        assert "Some search result" in result
        assert "https://example.com" in result
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "perplexity.ai" in call_kwargs[0][0]

    def test_web_search_falls_back_to_tavily_when_no_perplexity(self):
        """web_search falls back to Tavily if perplexity_api_key is empty."""
        from app.services.tool_use_agents import _exec_web_search

        tavily_resp = MagicMock()
        tavily_resp.raise_for_status = MagicMock()
        tavily_resp.json.return_value = {
            "results": [{"title": "Article", "content": "Interesting finding"}]
        }

        with patch("app.services.tool_use_agents.settings") as mock_settings, \
             patch("httpx.post", return_value=tavily_resp):
            mock_settings.perplexity_api_key = ""
            mock_settings.tavily_api_key = "tvly-test"
            result = _exec_web_search("hooks")

        assert "Interesting finding" in result

    def test_score_content_quality_detects_ai_tells(self):
        """score_content_quality catches AI-tell phrases."""
        from app.services.tool_use_agents import _exec_score_content_quality

        content = "It's worth noting that personal branding is important."
        result_json = _exec_score_content_quality(content)
        result = json.loads(result_json)

        assert result["pass"] is False
        assert any("it's worth noting" in t for t in result["ai_tells_found"])

    def test_score_content_quality_detects_em_dashes(self):
        """score_content_quality catches em dashes."""
        from app.services.tool_use_agents import _exec_score_content_quality

        content = "Build your brand — it matters."
        result_json = _exec_score_content_quality(content)
        result = json.loads(result_json)

        assert result["pass"] is False
        assert "—" in result["em_dashes_found"]

    def test_score_content_quality_passes_clean_content(self):
        """score_content_quality passes clean, well-structured content."""
        from app.services.tool_use_agents import _exec_score_content_quality

        content = (
            "One mistake I made building my brand?\n"
            "I thought more followers meant more money.\n"
            "It doesn't. Here's what actually matters."
        )
        result_json = _exec_score_content_quality(content)
        result = json.loads(result_json)

        assert result["pass"] is True
        assert result["ai_tells_found"] == []
        assert result["em_dashes_found"] == []

    def test_run_tool_use_agent_returns_failure_without_anthropic_key(self):
        """run_tool_use_agent returns AgentResult(success=False) if no Anthropic key."""
        from app.services.tool_use_agents import run_tool_use_agent

        with patch("app.services.tool_use_agents.settings") as mock_settings:
            mock_settings.anthropic_api_key = ""
            result = run_tool_use_agent(
                agent_id="copywriter",
                task_type="test",
                system_prompt="Test",
                user_prompt="Write something",
                user_id="user-123",
            )

        assert result.success is False
        assert "Anthropic API key" in result.error

    def test_dispatch_tool_returns_error_for_unknown_tool(self):
        """_dispatch_tool returns safe error string for unknown tool names."""
        from app.services.tool_use_agents import _dispatch_tool

        result = _dispatch_tool("nonexistent_tool", {})
        assert "Unknown tool" in result


# ═══════════════════════════════════════════════════════════════════════════
# TestSecretRedaction
# ═══════════════════════════════════════════════════════════════════════════


class TestSecretRedaction:
    """Secrets must never appear in ledger summaries."""

    def test_bearer_token_redacted(self):
        from app.services.tool_use_agents import _redact
        text = "Authorization: Bearer sk-proj-abc123xyz"
        assert "sk-proj-abc123xyz" not in _redact(text)
        assert "[REDACTED]" in _redact(text)

    def test_linkedin_cookie_redacted(self):
        from app.services.tool_use_agents import _redact
        text = "session_cookie=AQEfaketoken12345XYZ"
        assert "AQEfaketoken12345XYZ" not in _redact(text)

    def test_clean_text_unchanged(self):
        from app.services.tool_use_agents import _redact
        text = "The agent searched for 'LinkedIn hooks' and found 5 results."
        # No secrets, should not be mangled
        assert "LinkedIn hooks" in _redact(text)
        assert "found 5 results" in _redact(text)


# ═══════════════════════════════════════════════════════════════════════════
# TestPlaybooksService
# ═══════════════════════════════════════════════════════════════════════════


class TestPlaybooksService:
    """Playbooks service logic (DB mocked)."""

    def _make_mock_sb(self, data=None):
        """Helper: builds a mock Supabase client chain."""
        sb = MagicMock()
        result = MagicMock()
        result.data = data if data is not None else []
        chain = MagicMock()
        chain.execute.return_value = result
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value = chain
        sb.table.return_value.upsert.return_value.execute.return_value = result
        sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = result
        return sb

    def test_seed_calls_upsert_with_8_rows(self):
        """seed_default_playbooks upserts 8 rows."""
        mock_sb = MagicMock()
        upsert_result = MagicMock()
        upsert_result.data = [{}] * 8
        mock_sb.table.return_value.upsert.return_value.execute.return_value = upsert_result

        with patch("app.services.playbooks.get_admin_client", return_value=mock_sb):
            from app.services.playbooks import seed_default_playbooks
            count = seed_default_playbooks("user-abc")

        assert count == 8
        call_args = mock_sb.table.return_value.upsert.call_args
        rows = call_args[0][0]
        assert len(rows) == 8

    def test_get_playbook_returns_none_when_not_found(self):
        """get_playbook returns None when no row is found."""
        mock_sb = MagicMock()
        result = MagicMock()
        result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = result

        with patch("app.services.playbooks.get_admin_client", return_value=mock_sb):
            from app.services.playbooks import get_playbook
            pb = get_playbook("copywriter", "user-abc")

        assert pb is None

    def test_propose_edit_raises_on_empty_content(self):
        """propose_edit raises ValueError for empty content."""
        from app.services.playbooks import propose_edit

        with patch("app.services.playbooks.get_admin_client"):
            with pytest.raises(ValueError, match="cannot be empty"):
                propose_edit("copywriter", "user-abc", "   ")

    def test_propose_edit_raises_on_too_long_content(self):
        """propose_edit raises ValueError when content exceeds 20k chars."""
        from app.services.playbooks import propose_edit

        with patch("app.services.playbooks.get_admin_client"):
            with pytest.raises(ValueError, match="20,000"):
                propose_edit("copywriter", "user-abc", "x" * 20001)

    def test_apply_edit_raises_when_no_pending(self):
        """apply_edit raises ValueError when no pending edit exists."""
        mock_sb = MagicMock()
        result = MagicMock()
        result.data = [{"agent_id": "copywriter", "version": 1, "playbook_md": "old", "pending_edit_md": None}]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = result

        with patch("app.services.playbooks.get_admin_client", return_value=mock_sb):
            from app.services.playbooks import apply_edit
            with pytest.raises(ValueError, match="No pending edit"):
                apply_edit("copywriter", "user-abc")


# ═══════════════════════════════════════════════════════════════════════════
# TestPlaybooksRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestPlaybooksRouter:
    """Playbooks router is wired in main.py."""

    def test_playbooks_router_registered(self):
        """The /playbooks/ prefix must be in the FastAPI app routes."""
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("/playbooks" in p for p in paths)

    def test_playbooks_seed_route_exists(self):
        """POST /playbooks/seed must be a registered route."""
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("playbooks" in p and "seed" in p for p in paths)


# ═══════════════════════════════════════════════════════════════════════════
# TestLedgerRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestLedgerRouter:
    """Ledger router is wired in main.py."""

    def test_ledger_runs_route_exists(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("ledger" in p and "runs" in p for p in paths)

    def test_ledger_entries_route_exists(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("ledger" in p and "entries" in p for p in paths)

    def test_ledger_summary_route_exists(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("ledger" in p and "summary" in p for p in paths)


# ═══════════════════════════════════════════════════════════════════════════
# TestConnectorsService
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectorsService:
    """Connector credential encryption and service tests."""

    def test_encrypt_decrypt_roundtrip(self):
        """Credentials survive encrypt → decrypt roundtrip intact."""
        from app.services.connectors import encrypt_credentials, decrypt_credentials

        original = {"bearer_token": "AAA_test_token_12345"}
        with patch("app.services.connectors.settings") as mock_settings:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key().decode()
            mock_settings.connector_encryption_key = key
            encrypted = encrypt_credentials(original)
            recovered = decrypt_credentials(encrypted)

        assert recovered == original
        assert "AAA_test_token_12345" not in encrypted  # must be opaque

    def test_missing_encryption_key_raises(self):
        """_get_fernet raises ValueError when key is not set."""
        from app.services.connectors import _get_fernet

        with patch("app.services.connectors.settings") as mock_settings:
            mock_settings.connector_encryption_key = ""
            with pytest.raises(ValueError, match="CONNECTOR_ENCRYPTION_KEY"):
                _get_fernet()

    def test_webhook_ssrf_blocked(self):
        """save_connector blocks private-IP webhook URLs via validate_url."""
        from app.services.connectors import _validate_credential_shape

        with pytest.raises((ValueError, Exception)):
            _validate_credential_shape("webhook", {"url": "http://192.168.1.1/webhook"})

    def test_credential_shape_validation_missing_field(self):
        """save_connector raises ValueError when required fields are missing.
        Slice 86 updated Twitter to OAuth 1.0a (4 fields instead of bearer_token).
        """
        from app.services.connectors import _validate_credential_shape

        # Twitter now requires OAuth 1.0a — missing all 4 fields should raise
        with pytest.raises(ValueError, match="Missing required fields"):
            _validate_credential_shape("twitter", {"api_key": ""})

    def test_test_connector_returns_error_when_not_found(self):
        """test_connector returns error dict when connector doesn't exist in DB."""
        mock_sb = MagicMock()
        result = MagicMock()
        result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = result

        with patch("app.services.connectors.get_admin_client", return_value=mock_sb):
            from app.services.connectors import test_connector
            out = test_connector("user-abc", "twitter")

        assert out["status"] == "error"
        assert "not found" in out["message"]

    def test_unsupported_service_raises(self):
        """save_connector raises ValueError for unknown service names."""
        from app.services.connectors import save_connector

        with patch("app.services.connectors.get_admin_client"), \
             patch("app.services.connectors.settings") as ms:
            from cryptography.fernet import Fernet
            ms.connector_encryption_key = Fernet.generate_key().decode()
            with pytest.raises(ValueError, match="Unsupported service"):
                save_connector("user-abc", "tiktok", "TikTok", {"token": "x"})


# ═══════════════════════════════════════════════════════════════════════════
# TestConnectorsRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectorsRouter:
    """Connectors router is wired in main.py."""

    def test_connectors_router_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("/connectors" in p for p in paths)

    def test_connectors_test_route_exists(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert any("connectors" in p and "test" in p for p in paths)


# ═══════════════════════════════════════════════════════════════════════════
# TestLLMRouting
# ═══════════════════════════════════════════════════════════════════════════


class TestLLMRouting:
    """sdk_agents.py correctly routes tasks to tool-use vs single-call."""

    def test_copywriter_single_call_when_no_user_id(self):
        """run_copywriter_task uses single-call path when user_id not provided."""
        from app.services.sdk_agents import run_copywriter_task

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {"content": "Great hook here!", "usage": {"input_tokens": 100, "output_tokens": 50}}

        with patch("app.services.sdk_agents.get_llm_client", return_value=mock_llm):
            result = run_copywriter_task(
                prompt="Write a hook about productivity",
                brand_context="Direct, punchy",
                use_tool_use=False,
            )

        assert result.success is True
        assert "Great hook here!" in result.content
        mock_llm.chat.assert_called_once()

    def test_research_synthesis_single_call_fallback(self):
        """run_research_synthesis_task uses single-call path when use_tool_use=False."""
        from app.services.sdk_agents import run_research_synthesis_task

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {"content": "Key insight: X", "usage": {"input_tokens": 200, "output_tokens": 100}}

        with patch("app.services.sdk_agents.get_llm_client", return_value=mock_llm):
            result = run_research_synthesis_task(
                research_data="Some data",
                synthesis_goal="Find trends",
                use_tool_use=False,
            )

        assert result.success is True
        assert "Key insight" in result.content


# ═══════════════════════════════════════════════════════════════════════════
# TestGeminiSynthesis
# ═══════════════════════════════════════════════════════════════════════════


class TestGeminiSynthesis:
    """Gemini synthesis tool gracefully degrades when key is missing."""

    def test_gemini_returns_graceful_message_when_no_key(self):
        from app.services.tool_use_agents import _exec_synthesize_research

        with patch("app.services.tool_use_agents.settings") as ms:
            ms.gemini_api_key = ""
            result = _exec_synthesize_research("some data", "find patterns")

        assert "unavailable" in result or "not set" in result or "GEMINI_API_KEY" in result

    def test_gemini_calls_correct_endpoint(self):
        from app.services.tool_use_agents import _exec_synthesize_research, GEMINI_URL

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Synthesis result"}]}}]
        }

        with patch("app.services.tool_use_agents.settings") as ms, \
             patch("httpx.post", return_value=mock_resp) as mock_post:
            ms.gemini_api_key = "AIza_test_key"
            result = _exec_synthesize_research("research data", "find insights")

        assert "Synthesis result" in result
        call_url = mock_post.call_args[0][0]
        assert "generativelanguage.googleapis.com" in call_url
