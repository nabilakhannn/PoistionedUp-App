"""Tests for LLM reliability improvements (Slice 82).

Validates:
  - OpenAI client has proper timeout configuration
  - OpenAI client disables SDK-level retries (we handle retries ourselves)
  - Retry constants are tuned for Vercel serverless (120s max)
  - run_all is ignored (always runs one stage at a time)
  - brand_research._llm_call has no duplicate retry loop
  - Connection errors produce user-friendly messages
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── OpenAI client timeout tests ──────────────────────────────


class TestOpenAIClientTimeout:
    """Verify the OpenAI client is created with proper timeout config."""

    def test_openai_client_has_timeout(self):
        """OpenAI client must have an explicit timeout to prevent hanging on serverless."""
        from worker.graph.llm import OpenAIClient

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_openai_cls.return_value = MagicMock()
            OpenAIClient(api_key="test-key")

            # Verify OpenAI was called with a timeout parameter
            call_kwargs = mock_openai_cls.call_args
            assert "timeout" in call_kwargs.kwargs, (
                "OpenAI client must be created with an explicit timeout"
            )

    def test_openai_client_no_sdk_retries(self):
        """OpenAI SDK retries must be disabled — we handle retries in _chat_openai."""
        from worker.graph.llm import OpenAIClient

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_openai_cls.return_value = MagicMock()
            OpenAIClient(api_key="test-key")

            call_kwargs = mock_openai_cls.call_args
            assert call_kwargs.kwargs.get("max_retries") == 0, (
                "OpenAI SDK retries must be 0 — we handle retries ourselves"
            )


# ── Retry constants tests ────────────────────────────────────


class TestRetryConstants:
    """Verify retry constants are safe for Vercel serverless."""

    def test_max_retries_serverless_safe(self):
        """MAX_RETRIES must be <= 2 to fit within Vercel's 120s timeout."""
        from worker.graph.llm import MAX_RETRIES
        assert MAX_RETRIES <= 2, f"MAX_RETRIES={MAX_RETRIES} too high for serverless"

    def test_retry_max_delay_serverless_safe(self):
        """RETRY_MAX_DELAY must be <= 10s to avoid wasting timeout budget."""
        from worker.graph.llm import RETRY_MAX_DELAY
        assert RETRY_MAX_DELAY <= 10.0, f"RETRY_MAX_DELAY={RETRY_MAX_DELAY}s too high"


# ── run_all disabled tests ───────────────────────────────────


class TestRunAllDisabled:
    """Verify run_all mode is disabled to prevent serverless timeouts."""

    def test_run_all_ignored(self):
        """POST with run_all=True must still run only one stage."""
        from app.routers.brands import run_research_stage

        source = inspect.getsource(run_research_stage)
        assert "run_all_stages" not in source, (
            "run_research_stage must not call run_all_stages — "
            "it would exceed Vercel's serverless timeout"
        )


# ── brand_research no duplicate retry ────────────────────────


class TestNoDuplicateRetry:
    """Verify brand_research._llm_call delegates retries to llm.py."""

    def test_llm_call_no_retry_loop(self):
        """_llm_call must not have its own retry loop (llm.py handles retries)."""
        from app.services.brand_research import _llm_call

        source = inspect.getsource(_llm_call)
        assert "for attempt" not in source, (
            "_llm_call must not have a retry loop — llm.py handles retries"
        )
        assert "time.sleep" not in source, (
            "_llm_call must not sleep between retries — llm.py handles this"
        )


# ── Connection error friendly message ────────────────────────


class TestConnectionErrorMessage:
    """Verify connection errors produce user-friendly messages."""

    def test_connection_error_friendly_message(self):
        """run_stage must produce a friendly error for connection/timeout failures."""
        from app.services.brand_research import run_stage

        source = inspect.getsource(run_stage)
        assert "temporarily unavailable" in source, (
            "run_stage must show a user-friendly message for connection errors"
        )
