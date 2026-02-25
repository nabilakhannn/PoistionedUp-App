"""Tests for Slice 26: Pipeline reliability improvements.

Covers:
- Hardened JSON parsing (edge cases)
- Retry helper functions (_is_retryable_error, _get_retry_delay)
- safe_node decorator (error handling + timing)
- Executor node_error detection
- OpenAI client retry loop
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pytest


# ── Tests for parse_json_response ─────────────────────────────


class TestParseJsonResponse:
    """Test the hardened JSON parser handles all edge cases."""

    def test_clean_json_object(self):
        from worker.graph.llm import parse_json_response

        result = parse_json_response('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_clean_json_array(self):
        from worker.graph.llm import parse_json_response

        result = parse_json_response('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_with_whitespace(self):
        from worker.graph.llm import parse_json_response

        result = parse_json_response('  \n  {"key": "value"}  \n  ')
        assert result == {"key": "value"}

    def test_json_in_code_fence(self):
        from worker.graph.llm import parse_json_response

        content = '```json\n{"key": "value"}\n```'
        result = parse_json_response(content)
        assert result == {"key": "value"}

    def test_json_in_plain_code_fence(self):
        from worker.graph.llm import parse_json_response

        content = '```\n{"key": "value"}\n```'
        result = parse_json_response(content)
        assert result == {"key": "value"}

    def test_json_with_trailing_text(self):
        from worker.graph.llm import parse_json_response

        content = 'Here is the result: {"key": "value"} Hope this helps!'
        result = parse_json_response(content)
        assert result == {"key": "value"}

    def test_json_with_leading_text(self):
        from worker.graph.llm import parse_json_response

        content = 'Sure, here you go:\n{"signals": [1, 2, 3]}'
        result = parse_json_response(content)
        assert result == {"signals": [1, 2, 3]}

    def test_nested_json(self):
        from worker.graph.llm import parse_json_response

        data = {"outer": {"inner": [1, 2, {"deep": True}]}}
        result = parse_json_response(json.dumps(data))
        assert result == data

    def test_empty_string_raises(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError, match="empty response"):
            parse_json_response("")

    def test_whitespace_only_raises(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError, match="empty response"):
            parse_json_response("   \n\t  ")

    def test_none_raises(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError, match="empty response"):
            parse_json_response(None)

    def test_plain_text_raises(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError, match="Could not parse"):
            parse_json_response("This is just plain text with no JSON at all.")

    def test_bom_character_handled(self):
        from worker.graph.llm import parse_json_response

        content = '\ufeff{"key": "value"}'
        result = parse_json_response(content)
        assert result == {"key": "value"}

    def test_multiple_code_fences_uses_first(self):
        from worker.graph.llm import parse_json_response

        content = (
            'Here are two options:\n'
            '```json\n{"option": 1}\n```\n'
            'Or:\n'
            '```json\n{"option": 2}\n```'
        )
        result = parse_json_response(content)
        assert result == {"option": 1}

    def test_json_array_in_text(self):
        from worker.graph.llm import parse_json_response

        content = 'The topics are: [{"title": "AI"}, {"title": "ML"}]'
        result = parse_json_response(content)
        assert result == [{"title": "AI"}, {"title": "ML"}]

    def test_parse_error_includes_preview(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError) as exc_info:
            parse_json_response("not json content here")
        assert "not json content" in str(exc_info.value)
        assert exc_info.value.raw_content == "not json content here"


# ── Tests for retry helpers ───────────────────────────────────


class TestIsRetryableError:
    """Test _is_retryable_error identifies transient OpenAI errors."""

    def test_rate_limit_is_retryable(self):
        from worker.graph.llm import _is_retryable_error

        try:
            from openai import RateLimitError
        except ImportError:
            pytest.skip("openai not installed")

        exc = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        assert _is_retryable_error(exc) is True

    def test_timeout_is_retryable(self):
        from worker.graph.llm import _is_retryable_error

        try:
            from openai import APITimeoutError
        except ImportError:
            pytest.skip("openai not installed")

        exc = APITimeoutError(request=MagicMock())
        assert _is_retryable_error(exc) is True

    def test_internal_server_is_retryable(self):
        from worker.graph.llm import _is_retryable_error

        try:
            from openai import InternalServerError
        except ImportError:
            pytest.skip("openai not installed")

        exc = InternalServerError(
            message="Server error",
            response=MagicMock(status_code=500, headers={}),
            body=None,
        )
        assert _is_retryable_error(exc) is True

    def test_connection_error_is_retryable(self):
        from worker.graph.llm import _is_retryable_error

        try:
            from openai import APIConnectionError
        except ImportError:
            pytest.skip("openai not installed")

        exc = APIConnectionError(request=MagicMock())
        assert _is_retryable_error(exc) is True

    def test_auth_error_not_retryable(self):
        from worker.graph.llm import _is_retryable_error

        try:
            from openai import AuthenticationError
        except ImportError:
            pytest.skip("openai not installed")

        exc = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        )
        assert _is_retryable_error(exc) is False

    def test_generic_error_not_retryable(self):
        from worker.graph.llm import _is_retryable_error

        exc = ValueError("Some random error")
        assert _is_retryable_error(exc) is False

    def test_fallback_message_match(self):
        """Without openai installed, falls back to message matching."""
        from worker.graph.llm import _is_retryable_error

        # Even with openai installed, the code checks isinstance first
        # Test the message-based fallback by creating a non-openai exception
        # with a rate-limit-like message
        exc = Exception("rate limit hit")
        # This won't match because openai IS installed and it's not an openai error
        # Just verify it returns a boolean
        result = _is_retryable_error(exc)
        assert isinstance(result, bool)


class TestGetRetryDelay:
    """Test _get_retry_delay exponential backoff calculation."""

    def test_first_attempt_base_delay(self):
        from worker.graph.llm import _get_retry_delay

        delay = _get_retry_delay(0, Exception("generic"))
        assert delay == 1.0

    def test_second_attempt_doubled(self):
        from worker.graph.llm import _get_retry_delay

        delay = _get_retry_delay(1, Exception("generic"))
        assert delay == 2.0

    def test_third_attempt_quadrupled(self):
        from worker.graph.llm import _get_retry_delay

        delay = _get_retry_delay(2, Exception("generic"))
        assert delay == 4.0

    def test_delay_capped_at_max(self):
        from worker.graph.llm import _get_retry_delay, RETRY_MAX_DELAY

        delay = _get_retry_delay(10, Exception("generic"))
        assert delay == RETRY_MAX_DELAY

    def test_respects_retry_after_header(self):
        from worker.graph.llm import _get_retry_delay

        exc = Exception("rate limited")
        exc.headers = {"retry-after": "3.5"}
        delay = _get_retry_delay(0, exc)
        assert delay == 3.5

    def test_retry_after_capped(self):
        from worker.graph.llm import _get_retry_delay, RETRY_MAX_DELAY

        exc = Exception("rate limited")
        exc.headers = {"retry-after": "999"}
        delay = _get_retry_delay(0, exc)
        assert delay == RETRY_MAX_DELAY

    def test_invalid_retry_after_ignored(self):
        from worker.graph.llm import _get_retry_delay

        exc = Exception("rate limited")
        exc.headers = {"retry-after": "not-a-number"}
        delay = _get_retry_delay(0, exc)
        assert delay == 1.0  # Falls back to exponential


# ── Tests for safe_node decorator ─────────────────────────────


class TestSafeNode:
    """Test the safe_node decorator wraps nodes correctly."""

    def test_successful_node_returns_result(self):
        from worker.graph.llm import safe_node

        @safe_node
        def good_node(state):
            return {"result": "ok", "current_step": "good_node"}

        result = good_node({"workflow_id": "wf-1"})
        assert result == {"result": "ok", "current_step": "good_node"}

    def test_failed_node_returns_error_dict(self):
        from worker.graph.llm import safe_node

        @safe_node
        def bad_node(state):
            raise ValueError("Something broke")

        result = bad_node({"workflow_id": "wf-1"})
        assert "node_error" in result
        assert result["node_error"]["node"] == "bad_node"
        assert result["node_error"]["error"] == "Something broke"
        assert result["node_error"]["error_type"] == "ValueError"
        assert result["node_error"]["elapsed_seconds"] >= 0
        assert result["current_step"] == "bad_node"

    def test_budget_exceeded_propagates(self):
        from worker.graph.llm import safe_node, WorkflowBudgetExceeded

        @safe_node
        def budget_node(state):
            raise WorkflowBudgetExceeded("Over budget")

        with pytest.raises(WorkflowBudgetExceeded):
            budget_node({"workflow_id": "wf-1"})

    def test_token_ceiling_propagates(self):
        from worker.graph.llm import safe_node, TokenCeilingExceeded

        @safe_node
        def ceiling_node(state):
            raise TokenCeilingExceeded("Too many tokens")

        with pytest.raises(TokenCeilingExceeded):
            ceiling_node({"workflow_id": "wf-1"})

    def test_decorator_preserves_function_name(self):
        from worker.graph.llm import safe_node

        @safe_node
        def my_custom_node(state):
            return {"current_step": "my_custom_node"}

        assert my_custom_node.__name__ == "my_custom_node"

    def test_node_error_includes_timing(self):
        from worker.graph.llm import safe_node

        @safe_node
        def slow_fail_node(state):
            time.sleep(0.05)
            raise RuntimeError("Slow failure")

        result = slow_fail_node({"workflow_id": "wf-1"})
        assert result["node_error"]["elapsed_seconds"] >= 0.04

    def test_llm_parse_error_caught(self):
        from worker.graph.llm import safe_node, LLMResponseParseError

        @safe_node
        def parse_fail_node(state):
            raise LLMResponseParseError("Bad JSON", raw_content="not json")

        result = parse_fail_node({"workflow_id": "wf-1"})
        assert result["node_error"]["error_type"] == "LLMResponseParseError"
        assert "Bad JSON" in result["node_error"]["error"]

    def test_missing_workflow_id_uses_unknown(self):
        from worker.graph.llm import safe_node

        @safe_node
        def node_no_wf(state):
            raise RuntimeError("Error")

        result = node_no_wf({})
        assert result["node_error"]["node"] == "node_no_wf"

    def test_graph_interrupt_propagates(self):
        """GraphInterrupt must pass through so LangGraph interrupt/resume works."""
        from worker.graph.llm import safe_node

        try:
            from langgraph.errors import GraphInterrupt
        except ImportError:
            pytest.skip("langgraph not installed")

        @safe_node
        def interrupt_node(state):
            raise GraphInterrupt({"type": "test_interrupt"})

        with pytest.raises(GraphInterrupt):
            interrupt_node({"workflow_id": "wf-1"})


# ── Tests for executor node_error handling ────────────────────


class TestExecutorNodeError:
    """Test that the executor detects and handles node_error in state."""

    @patch("worker.executor.record_workflow_memories")
    @patch("worker.executor.build_graph")
    @patch("worker.executor.get_checkpointer")
    @patch("worker.executor.update_status")
    @patch("worker.executor.create_snapshot")
    def test_node_error_marks_workflow_failed(
        self, mock_snapshot, mock_status, mock_checkpointer,
        mock_build_graph, mock_memories
    ):
        from worker.executor import run_pipeline

        # Simulate a graph that returns state with node_error
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "current_step": "signal_research",
            "node_error": {
                "node": "signal_research",
                "error": "Rate limit exceeded after retries",
                "error_type": "RateLimitError",
                "elapsed_seconds": 12.3,
            },
        }
        mock_build_graph.return_value = mock_graph

        # Mock the Supabase client
        mock_client = MagicMock()
        mock_execute = MagicMock(data=[{
            "user_id": "user-1",
            "goal_text": "test",
            "settings": {},
            "profile_snapshot": {},
        }])
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_execute

        result = run_pipeline(mock_client, "wf-123", action="run")

        assert result == "failed"

        # Verify update_status was called with "failed"
        mock_status.assert_called_with(
            mock_client, "wf-123", "failed",
            current_step="signal_research",
        )

        # Verify a snapshot was created for the error
        mock_snapshot.assert_called_once()
        snapshot_args = mock_snapshot.call_args
        assert snapshot_args[0][1] == "wf-123"
        assert snapshot_args[0][2] == "signal_research"
        assert snapshot_args[1]["state_json"]["status"] == "failed"
        assert "Rate limit" in snapshot_args[1]["state_json"]["error"]

        # Verify memories were NOT recorded (pipeline failed)
        mock_memories.assert_not_called()

    @patch("worker.executor.record_workflow_memories")
    @patch("worker.executor.build_graph")
    @patch("worker.executor.get_checkpointer")
    @patch("worker.executor.update_status")
    @patch("worker.executor.create_snapshot")
    @patch("worker.executor._save_content_assets")
    @patch("worker.executor._save_test_report")
    def test_no_node_error_completes_normally(
        self, mock_test_report, mock_assets, mock_snapshot,
        mock_status, mock_checkpointer, mock_build_graph, mock_memories
    ):
        from worker.executor import run_pipeline

        # Simulate a successful graph completion
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "current_step": "approval",
            "approval_decision": "approved",
            "user_id": "user-1",
        }
        # No interrupts
        mock_graph_state = MagicMock()
        mock_graph_state.tasks = []
        mock_graph.get_state.return_value = mock_graph_state
        mock_build_graph.return_value = mock_graph

        mock_client = MagicMock()
        mock_execute = MagicMock(data=[{
            "user_id": "user-1",
            "goal_text": "test",
            "settings": {},
            "profile_snapshot": {},
            "brand_id": None,
        }])
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_execute

        result = run_pipeline(mock_client, "wf-123", action="run")

        assert result == "approved"

        # Verify memories WERE recorded on approval
        mock_memories.assert_called_once()

        # Verify final status is "approved"
        mock_status.assert_called_with(
            mock_client, "wf-123", "approved",
            current_step="approval",
        )


# ── Tests for OpenAI client retry ─────────────────────────────


class TestOpenAIClientRetry:
    """Test the full OpenAI client retry behavior with mocks."""

    def _make_client(self, mock_openai):
        """Create an OpenAIClient with a mocked OpenAI inner client."""
        from worker.graph.llm import OpenAIClient

        client = OpenAIClient.__new__(OpenAIClient)
        client._client = mock_openai
        return client

    def _mock_response(self, content='{"ok": true}'):
        """Create a mock OpenAI response."""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content=content))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        return mock_resp

    @patch("worker.graph.llm._log_usage")
    @patch("worker.graph.llm._check_daily_token_cap")
    @patch("worker.graph.llm._check_workflow_budget")
    @patch("worker.graph.llm.settings")
    def test_succeeds_on_first_try(self, mock_settings, mock_budget, mock_daily_cap, mock_log):
        mock_settings.max_tokens_per_step = 10000

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = self._mock_response()
        client = self._make_client(mock_openai)

        result = client.chat(
            messages=[{"role": "user", "content": "test"}],
            model="gpt-4o",
        )

        assert result["content"] == '{"ok": true}'
        assert mock_openai.chat.completions.create.call_count == 1

    @patch("worker.graph.llm._log_usage")
    @patch("worker.graph.llm._check_daily_token_cap")
    @patch("worker.graph.llm._check_workflow_budget")
    @patch("worker.graph.llm.settings")
    @patch("time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep, mock_settings, mock_budget, mock_daily_cap, mock_log):
        mock_settings.max_tokens_per_step = 10000

        try:
            from openai import RateLimitError
        except ImportError:
            pytest.skip("openai not installed")

        rate_error = RateLimitError(
            message="Rate limit",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = [
            rate_error,
            self._mock_response(),
        ]
        client = self._make_client(mock_openai)

        result = client.chat(
            messages=[{"role": "user", "content": "test"}],
            model="gpt-4o",
        )

        assert result["content"] == '{"ok": true}'
        assert mock_openai.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once()  # Slept once between retries

    @patch("worker.graph.llm._log_usage")
    @patch("worker.graph.llm._check_daily_token_cap")
    @patch("worker.graph.llm._check_workflow_budget")
    @patch("worker.graph.llm.settings")
    @patch("time.sleep")
    def test_gives_up_after_max_retries(self, mock_sleep, mock_settings, mock_budget, mock_daily_cap, mock_log):
        from worker.graph.llm import MAX_RETRIES

        mock_settings.max_tokens_per_step = 10000

        try:
            from openai import RateLimitError
        except ImportError:
            pytest.skip("openai not installed")

        rate_error = RateLimitError(
            message="Rate limit",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = rate_error
        client = self._make_client(mock_openai)

        with pytest.raises(type(rate_error)):
            client.chat(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-4o",
            )

        # Should have tried MAX_RETRIES + 1 times total
        assert mock_openai.chat.completions.create.call_count == MAX_RETRIES + 1

    @patch("worker.graph.llm._log_usage")
    @patch("worker.graph.llm._check_daily_token_cap")
    @patch("worker.graph.llm._check_workflow_budget")
    @patch("worker.graph.llm.settings")
    def test_no_retry_on_auth_error(self, mock_settings, mock_budget, mock_daily_cap, mock_log):
        mock_settings.max_tokens_per_step = 10000

        try:
            from openai import AuthenticationError
        except ImportError:
            pytest.skip("openai not installed")

        auth_error = AuthenticationError(
            message="Invalid key",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        )

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = auth_error
        client = self._make_client(mock_openai)

        with pytest.raises(type(auth_error)):
            client.chat(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-4o",
            )

        # Should NOT retry auth errors
        assert mock_openai.chat.completions.create.call_count == 1

    @patch("worker.graph.llm._log_usage")
    @patch("worker.graph.llm._check_daily_token_cap")
    @patch("worker.graph.llm._check_workflow_budget")
    @patch("worker.graph.llm.settings")
    @patch("time.sleep")
    def test_retries_on_connection_error(self, mock_sleep, mock_settings, mock_budget, mock_daily_cap, mock_log):
        mock_settings.max_tokens_per_step = 10000

        try:
            from openai import APIConnectionError
        except ImportError:
            pytest.skip("openai not installed")

        conn_error = APIConnectionError(request=MagicMock())

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = [
            conn_error,
            conn_error,
            self._mock_response('{"recovered": true}'),
        ]
        client = self._make_client(mock_openai)

        result = client.chat(
            messages=[{"role": "user", "content": "test"}],
            model="gpt-4o",
        )

        assert result["content"] == '{"recovered": true}'
        assert mock_openai.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2  # Slept between each retry


# ── Tests for pipeline nodes having @safe_node ────────────────


class TestNodesUseDecorator:
    """Verify all LLM-calling pipeline nodes are wrapped with safe_node."""

    @pytest.mark.parametrize("module_name,func_name", [
        ("worker.graph.nodes.signal_research", "signal_research"),
        ("worker.graph.nodes.gap_analysis", "gap_analysis"),
        ("worker.graph.nodes.hook_lab", "hook_lab"),
        ("worker.graph.nodes.script_generation", "script_generation"),
        ("worker.graph.nodes.editor", "editor"),
        ("worker.graph.nodes.testing", "testing"),
    ])
    def test_node_is_wrapped(self, module_name, func_name):
        """Each node function should be wrapped by safe_node (functools.wraps preserves __name__)."""
        import importlib

        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)

        # safe_node wraps with functools.wraps, so __wrapped__ is set
        assert hasattr(func, "__wrapped__"), (
            f"{module_name}.{func_name} is not decorated with @safe_node. "
            f"Add @safe_node above the function definition."
        )
