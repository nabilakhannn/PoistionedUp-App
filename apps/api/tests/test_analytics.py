"""Tests for the PostHog analytics service.

Verifies that the analytics service correctly wraps the PostHog SDK,
gracefully no-ops when keys are missing, and tracks events properly.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_analytics_module():
    """Reset the module-level globals so each test starts fresh."""
    import app.services.analytics as mod
    mod._posthog_client = None
    mod._initialized = False
    return mod


# ---------------------------------------------------------------------------
# No-op when API key is missing
# ---------------------------------------------------------------------------

class TestNoOpWithoutKey:
    """When POSTHOG_API_KEY is empty the service must silently no-op."""

    def test_track_event_noop(self):
        mod = _reset_analytics_module()
        with patch.object(mod, "_get_client", return_value=None):
            # Should not raise
            mod.track_event("user-1", "test_event", {"foo": "bar"})

    def test_identify_user_noop(self):
        mod = _reset_analytics_module()
        with patch.object(mod, "_get_client", return_value=None):
            mod.identify_user("user-1", {"email": "a@b.com"})

    def test_track_llm_event_noop(self):
        mod = _reset_analytics_module()
        with patch.object(mod, "_get_client", return_value=None):
            mod.track_llm_event(
                user_id="user-1",
                model="gpt-4o",
                step="signal_research",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=432.1,
            )

    def test_track_pipeline_event_noop(self):
        mod = _reset_analytics_module()
        with patch.object(mod, "_get_client", return_value=None):
            mod.track_pipeline_event(
                user_id="user-1",
                workflow_id="wf-123",
                event_type="started",
                step="signal_research",
            )

    def test_flush_noop(self):
        mod = _reset_analytics_module()
        with patch.object(mod, "_get_client", return_value=None):
            mod.flush()


# ---------------------------------------------------------------------------
# Track events when client is available
# ---------------------------------------------------------------------------

class TestTrackEventsWithClient:
    """When the PostHog client is available, events are forwarded."""

    def _make_mock_client(self):
        client = MagicMock()
        client.capture = MagicMock()
        client.identify = MagicMock()
        client.flush = MagicMock()
        return client

    def test_track_event_calls_capture(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_event("user-1", "workflow_created", {"platform": "youtube"})

        mock_client.capture.assert_called_once_with(
            distinct_id="user-1",
            event="workflow_created",
            properties={"platform": "youtube"},
        )

    def test_track_event_empty_properties(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_event("user-1", "some_event")

        mock_client.capture.assert_called_once_with(
            distinct_id="user-1",
            event="some_event",
            properties={},
        )

    def test_identify_user_calls_identify(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.identify_user("user-42", {"email": "test@example.com"})

        mock_client.identify.assert_called_once_with(
            "user-42", {"email": "test@example.com"}
        )

    def test_identify_user_empty_properties(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.identify_user("user-42")

        mock_client.identify.assert_called_once_with("user-42", {})

    def test_track_llm_event(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_llm_event(
                user_id="user-1",
                model="gpt-4o",
                step="hook_lab",
                prompt_tokens=500,
                completion_tokens=200,
                total_tokens=700,
                latency_ms=1234.5,
                workflow_id="wf-abc",
                success=True,
            )

        mock_client.capture.assert_called_once()
        call_args = mock_client.capture.call_args
        assert call_args.kwargs["distinct_id"] == "user-1"
        assert call_args.kwargs["event"] == "llm_api_call"
        props = call_args.kwargs["properties"]
        assert props["model"] == "gpt-4o"
        assert props["step"] == "hook_lab"
        assert props["prompt_tokens"] == 500
        assert props["completion_tokens"] == 200
        assert props["total_tokens"] == 700
        assert props["latency_ms"] == 1234.5
        assert props["workflow_id"] == "wf-abc"
        assert props["success"] is True

    def test_track_llm_event_with_error(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_llm_event(
                user_id="user-1",
                model="gpt-4o-mini",
                step="editor",
                success=False,
                error="Rate limit exceeded",
            )

        call_args = mock_client.capture.call_args
        props = call_args.kwargs["properties"]
        assert props["success"] is False
        assert props["error"] == "Rate limit exceeded"

    def test_track_pipeline_event(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_pipeline_event(
                user_id="user-1",
                workflow_id="wf-123",
                event_type="completed",
                step="approval",
                properties={"duration_s": 45.2},
            )

        mock_client.capture.assert_called_once()
        call_args = mock_client.capture.call_args
        assert call_args.kwargs["distinct_id"] == "user-1"
        assert call_args.kwargs["event"] == "pipeline_completed"
        props = call_args.kwargs["properties"]
        assert props["workflow_id"] == "wf-123"
        assert props["pipeline_event"] == "completed"
        assert props["step"] == "approval"
        assert props["duration_s"] == 45.2

    def test_track_pipeline_event_minimal(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_pipeline_event(
                user_id="user-1",
                workflow_id="wf-456",
                event_type="started",
            )

        call_args = mock_client.capture.call_args
        props = call_args.kwargs["properties"]
        assert props["workflow_id"] == "wf-456"
        assert props["pipeline_event"] == "started"
        assert "step" not in props

    def test_flush_calls_client(self):
        mod = _reset_analytics_module()
        mock_client = self._make_mock_client()
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.flush()

        mock_client.flush.assert_called_once()


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    """All analytics calls must swallow exceptions and never crash the app."""

    def test_track_event_swallows_exception(self):
        mod = _reset_analytics_module()
        mock_client = MagicMock()
        mock_client.capture.side_effect = RuntimeError("Network error")
        with patch.object(mod, "_get_client", return_value=mock_client):
            # Must not raise
            mod.track_event("user-1", "test_event")

    def test_identify_user_swallows_exception(self):
        mod = _reset_analytics_module()
        mock_client = MagicMock()
        mock_client.identify.side_effect = RuntimeError("Timeout")
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.identify_user("user-1")

    def test_flush_swallows_exception(self):
        mod = _reset_analytics_module()
        mock_client = MagicMock()
        mock_client.flush.side_effect = RuntimeError("Connection reset")
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.flush()

    def test_track_llm_event_swallows_exception(self):
        mod = _reset_analytics_module()
        mock_client = MagicMock()
        mock_client.capture.side_effect = Exception("Boom")
        with patch.object(mod, "_get_client", return_value=mock_client):
            mod.track_llm_event(
                user_id="user-1",
                model="gpt-4o",
                step="testing",
            )


# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------

class TestClientInitialization:
    """Tests for the lazy initialization logic."""

    def test_no_key_returns_none(self):
        mod = _reset_analytics_module()
        # Patch settings to have empty key
        mock_settings = MagicMock()
        mock_settings.posthog_api_key = ""
        mock_settings.posthog_host = "https://us.i.posthog.com"
        with patch("app.services.analytics.settings", mock_settings, create=True):
            # Need to re-import to trigger _get_client fresh
            mod._initialized = False
            mod._posthog_client = None
            # Patch the import inside _get_client
            with patch.dict("sys.modules", {"app.config": MagicMock(settings=mock_settings)}):
                result = mod._get_client()
        assert result is None

    def test_initialized_flag_prevents_reinit(self):
        mod = _reset_analytics_module()
        mock_client = MagicMock()
        mod._initialized = True
        mod._posthog_client = mock_client
        # Should return cached client without re-importing settings
        result = mod._get_client()
        assert result is mock_client

    def test_import_error_returns_none(self):
        mod = _reset_analytics_module()
        mock_settings = MagicMock()
        mock_settings.posthog_api_key = "phc_test_key_123"
        mock_settings.posthog_host = "https://us.i.posthog.com"
        with patch.dict("sys.modules", {"app.config": MagicMock(settings=mock_settings)}):
            with patch("builtins.__import__", side_effect=ImportError("no posthog")):
                mod._initialized = False
                mod._posthog_client = None
                result = mod._get_client()
        # The import of posthog will fail, but settings import might also fail.
        # Either way, result should be None
        assert result is None
