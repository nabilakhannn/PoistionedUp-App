"""LLM client wrapper for pipeline nodes.

Provides a mockable interface so pipeline tests can run without
hitting the real OpenAI API. In production, calls OpenAI's chat
completions endpoint OR Anthropic's Messages API depending on the
selected model.

Supports three model tiers:
  - budget:   GPT-4o-mini everywhere (~10x cheaper)
  - standard: Claude 3.5 Haiku for creative, GPT-4o-mini for review
  - premium:  Claude 3.5 Sonnet for creative, GPT-4o-mini for review

Includes automatic cost tracking (writes to usage_costs table),
per-step token ceiling enforcement, and exponential backoff retry
for transient errors (rate limits, timeouts, server errors).
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Protocol

from app.config import settings

logger = logging.getLogger("worker.graph.llm")

# ── Retry configuration ──────────────────────────────────────
MAX_RETRIES = 2
RETRY_BASE_DELAY = 1.0  # seconds
RETRY_BACKOFF_FACTOR = 2.0
RETRY_MAX_DELAY = 8.0  # cap — must fit within Vercel's 120s serverless timeout


# ── Cost estimation (USD per 1K tokens) ──────────────────────
# Fallback: when OpenAI is rate-limited or degraded, retry with these Anthropic models
_OPENAI_TO_ANTHROPIC_FALLBACK: dict[str, str] = {
    "gpt-4o": "claude-sonnet-4-6",
    "gpt-4o-mini": "claude-haiku-4-5-20251001",
    "gpt-4-turbo": "claude-sonnet-4-6",
    "gpt-4": "claude-sonnet-4-6",
    "gpt-3.5-turbo": "claude-haiku-4-5-20251001",
}

MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic
    "claude-3-5-haiku-latest": {"input": 0.0008, "output": 0.004},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
    "claude-3-opus-latest": {"input": 0.015, "output": 0.075},
    # Aliases
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    # Claude 4 models (fallback targets)
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
}


# ── Model Tiers ──────────────────────────────────────────────
# Each tier defines which models to use for creative vs review tasks.
# "creative" = brand chat, strategist, pipeline creative steps, content chat
# "review"   = pipeline review steps (editor, testing, approval)
# "embed"    = embeddings (always OpenAI, not affected by tier)

MODEL_TIERS = {
    "budget": {
        "label": "Budget",
        "description": "GPT-4o-mini for everything. Cheapest option, good quality for most tasks.",
        "creative": "gpt-4o-mini",
        "review": "gpt-4o-mini",
        "provider": "openai",
        "est_cost_per_workflow": "$0.01-0.03",
        "est_cost_per_chat_msg": "$0.001",
    },
    "standard": {
        "label": "Standard",
        "description": "Claude 3.5 Haiku for creative tasks, GPT-4o-mini for reviews. Great balance of quality and cost.",
        "creative": "claude-3-5-haiku-latest",
        "review": "gpt-4o-mini",
        "provider": "anthropic+openai",
        "est_cost_per_workflow": "$0.05-0.15",
        "est_cost_per_chat_msg": "$0.005",
    },
    "premium": {
        "label": "Premium",
        "description": "Claude 3.5 Sonnet for creative tasks, GPT-4o-mini for reviews. Best quality output.",
        "creative": "claude-3-5-sonnet-latest",
        "review": "gpt-4o-mini",
        "provider": "anthropic+openai",
        "est_cost_per_workflow": "$0.20-0.60",
        "est_cost_per_chat_msg": "$0.02",
    },
}

# Valid tier names
VALID_TIERS = list(MODEL_TIERS.keys())

# ── Model routing per pipeline step ─────────────────────────
# Maps step to "creative" or "review" category
STEP_CATEGORY = {
    "signal_research": "creative",
    "gap_analysis": "creative",
    "topic_selection": "creative",
    "hook_lab": "creative",
    "script_generation": "creative",
    "editor": "review",
    "testing": "review",
    "approval": "review",
}

# Legacy fallback: direct model mapping (used when no tier is set)
MODEL_FOR_STEP = {
    "signal_research": "gpt-4o",
    "gap_analysis": "gpt-4o",
    "topic_selection": "gpt-4o",
    "hook_lab": "gpt-4o",
    "script_generation": "gpt-4o",
    "editor": "gpt-4o-mini",
    "testing": "gpt-4o-mini",
    "approval": "gpt-4o-mini",
}


def get_model_for_step(step_id: str = "", tier: str = "") -> str:
    """Get the appropriate model for a given pipeline step and tier.

    If tier is provided, uses the tier's model mapping.
    If no tier, falls back to the legacy MODEL_FOR_STEP mapping.
    If no step is provided, uses the current tracking context step.
    """
    if not step_id:
        step_id = getattr(_tracking_context, "step_id", "") or ""

    if not tier:
        tier = getattr(_tracking_context, "model_tier", "") or ""

    if tier and tier in MODEL_TIERS:
        category = STEP_CATEGORY.get(step_id, "creative")
        return MODEL_TIERS[tier][category]

    return MODEL_FOR_STEP.get(step_id, "gpt-4o")


def get_model_for_chat(tier: str = "") -> str:
    """Get the appropriate model for chat (brand chat, strategist, content chat).

    Chat always uses the 'creative' model for the selected tier.
    """
    if tier and tier in MODEL_TIERS:
        return MODEL_TIERS[tier]["creative"]
    return "gpt-4o"  # Legacy default


def is_anthropic_model(model: str) -> bool:
    """Check if a model name is an Anthropic Claude model."""
    return model.startswith("claude")


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])
    return (input_tokens / 1000.0 * pricing["input"]) + (
        output_tokens / 1000.0 * pricing["output"]
    )


# ── Thread-local context for cost tracking ───────────────────
_tracking_context = threading.local()


def set_tracking_context(
    workflow_id: str, user_id: str, step_id: str, model_tier: str = "", request_id: str = ""
) -> None:
    """Set the context for cost tracking and correlation. Called by each pipeline node."""
    _tracking_context.workflow_id = workflow_id
    _tracking_context.user_id = user_id
    _tracking_context.step_id = step_id
    _tracking_context.model_tier = model_tier
    _tracking_context.request_id = request_id  # Propagate HTTP request_id for tracing


def clear_tracking_context() -> None:
    """Clear the tracking context after a node completes."""
    _tracking_context.workflow_id = None
    _tracking_context.user_id = None
    _tracking_context.step_id = None
    _tracking_context.model_tier = None
    _tracking_context.request_id = None


def _check_workflow_budget() -> None:
    """Check if the current workflow has exceeded its total token budget.

    Sums all usage_costs rows for the workflow and compares to max_tokens_per_workflow.
    Does nothing if no tracking context is set.
    """
    wf_id = getattr(_tracking_context, "workflow_id", None)
    if not wf_id:
        return

    workflow_ceiling = settings.max_tokens_per_workflow
    if workflow_ceiling <= 0:
        return

    try:
        from app.deps import get_admin_client

        admin = get_admin_client()
        resp = (
            admin.table("usage_costs")
            .select("input_tokens, output_tokens")
            .eq("workflow_id", wf_id)
            .execute()
        )

        total_tokens = 0
        for row in (resp.data or []):
            total_tokens += row.get("input_tokens", 0) + row.get("output_tokens", 0)

        if total_tokens >= workflow_ceiling:
            raise WorkflowBudgetExceeded(
                f"Workflow {wf_id} has used {total_tokens} tokens, "
                f"exceeding the per-workflow ceiling of {workflow_ceiling}."
            )

        # Log warning at 80% usage
        if total_tokens >= workflow_ceiling * 0.8:
            logger.warning(
                "Workflow %s at %d/%d tokens (%.0f%% of budget)",
                wf_id,
                total_tokens,
                workflow_ceiling,
                (total_tokens / workflow_ceiling) * 100,
            )
    except WorkflowBudgetExceeded:
        raise
    except Exception as e:
        # Don't block work if the budget check itself fails
        logger.warning("Workflow budget check failed (non-fatal): %s", e)


def _check_daily_token_cap() -> None:
    """Check if the current user has exceeded their daily token allowance.

    Sums all usage_costs rows for the user created today and compares
    to max_tokens_per_user_per_day. Does nothing if no tracking context is set.
    """
    uid = getattr(_tracking_context, "user_id", None)
    if not uid:
        return

    daily_ceiling = settings.max_tokens_per_user_per_day
    if daily_ceiling <= 0:
        return

    try:
        from datetime import datetime, timezone
        from app.deps import get_admin_client

        admin = get_admin_client()
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        resp = (
            admin.table("usage_costs")
            .select("input_tokens, output_tokens")
            .eq("user_id", uid)
            .gte("created_at", today_start.isoformat())
            .execute()
        )

        total_tokens = 0
        for row in (resp.data or []):
            total_tokens += row.get("input_tokens", 0) + row.get("output_tokens", 0)

        if total_tokens >= daily_ceiling:
            raise DailyTokenCapExceeded(
                "You have used %d tokens today, exceeding your daily limit "
                "of %d. Your allowance resets at midnight UTC." % (
                    total_tokens, daily_ceiling
                )
            )

        # Log warning at 80% usage
        if total_tokens >= daily_ceiling * 0.8:
            logger.warning(
                "User %s at %d/%d daily tokens (%.0f%% of cap)",
                uid,
                total_tokens,
                daily_ceiling,
                (total_tokens / daily_ceiling) * 100,
            )
    except DailyTokenCapExceeded:
        raise
    except Exception as e:
        # Don't block work if the cap check itself fails
        logger.warning("Daily token cap check failed (non-fatal): %s", e)


def _log_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    """Write a usage_costs row to Supabase. Fire-and-forget, never crashes."""
    wf_id = getattr(_tracking_context, "workflow_id", None)
    uid = getattr(_tracking_context, "user_id", None)
    step = getattr(_tracking_context, "step_id", None)

    if not wf_id or not uid:
        logger.debug("No tracking context set, skipping cost log")
        return

    cost = estimate_cost(model, input_tokens, output_tokens)

    try:
        from app.deps import get_admin_client

        admin = get_admin_client()
        admin.table("usage_costs").insert(
            {
                "workflow_id": wf_id,
                "user_id": uid,
                "step_id": step or "unknown",
                "model_name": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": float(cost),
            }
        ).execute()
        logger.debug(
            "Logged cost: wf=%s step=%s model=%s tokens=%d+%d cost=$%.6f",
            wf_id,
            step,
            model,
            input_tokens,
            output_tokens,
            cost,
        )
    except Exception as e:
        logger.warning("Failed to log usage cost: %s", e)


class TokenCeilingExceeded(Exception):
    """Raised when a single LLM call would exceed the per-step token ceiling."""


class WorkflowBudgetExceeded(Exception):
    """Raised when a workflow has exhausted its token budget."""


class DailyTokenCapExceeded(Exception):
    """Raised when a user has exhausted their daily token allowance."""


class LLMClient(Protocol):
    """Protocol for LLM calls, implement this for real or mock."""

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request.

        Returns {"content": str, "usage": {"input_tokens": int, "output_tokens": int}}
        """
        ...


def _is_retryable_error(exc: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    try:
        from openai import (
            RateLimitError,
            APITimeoutError,
            InternalServerError,
            APIConnectionError,
        )
        if isinstance(exc, (RateLimitError, APITimeoutError, InternalServerError, APIConnectionError)):
            return True
    except ImportError:
        pass

    # Check Anthropic errors
    try:
        from anthropic import (
            RateLimitError as AnthropicRateLimitError,
            APITimeoutError as AnthropicTimeoutError,
            InternalServerError as AnthropicInternalError,
            APIConnectionError as AnthropicConnectionError,
        )
        if isinstance(exc, (AnthropicRateLimitError, AnthropicTimeoutError, AnthropicInternalError, AnthropicConnectionError)):
            return True
    except ImportError:
        pass

    # Fallback: retry on common HTTP-like error messages
    msg = str(exc).lower()
    return any(kw in msg for kw in ["rate limit", "timeout", "502", "503", "504", "connection"])


def _get_retry_delay(attempt: int, exc: Exception) -> float:
    """Calculate retry delay with exponential backoff.

    If the error includes a Retry-After header, respect it.
    Otherwise use exponential backoff: 1s, 2s, 4s, capped at 16s.
    """
    # Check for Retry-After on rate limit errors
    retry_after = getattr(exc, "headers", {})
    if hasattr(retry_after, "get"):
        ra = retry_after.get("retry-after")
        if ra:
            try:
                return min(float(ra), RETRY_MAX_DELAY)
            except (ValueError, TypeError):
                pass

    delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
    return min(delay, RETRY_MAX_DELAY)


class OpenAIClient:
    """Real OpenAI client for production use.

    Automatically logs cost to usage_costs, checks token ceilings,
    and retries transient errors with exponential backoff.

    Now also supports Anthropic Claude models: when the model name
    starts with "claude", routes to the Anthropic Messages API instead.
    """

    def __init__(self, api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        import httpx
        from openai import OpenAI

        self._client = OpenAI(
            api_key=api_key or settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=5.0),
            max_retries=0,  # We handle retries ourselves in _chat_openai
        )
        self._anthropic_client = None
        self._anthropic_key = anthropic_api_key or settings.anthropic_api_key

    def _get_anthropic(self):
        """Lazy-init Anthropic client."""
        if self._anthropic_client is None:
            if not self._anthropic_key:
                raise ValueError(
                    "Anthropic API key not configured. Add ANTHROPIC_API_KEY to .env "
                    "or switch to Budget tier (uses OpenAI only)."
                )
            from anthropic import Anthropic
            self._anthropic_client = Anthropic(api_key=self._anthropic_key)
        return self._anthropic_client

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        # ── Per-step token ceiling ───────────────────────────
        ceiling = settings.max_tokens_per_step
        if max_tokens > ceiling:
            logger.warning(
                "Clamping max_tokens from %d to ceiling %d",
                max_tokens,
                ceiling,
            )
            max_tokens = ceiling

        # ── Per-workflow budget check ────────────────────────
        _check_workflow_budget()

        # ── Per-user daily token cap ─────────────────────────
        _check_daily_token_cap()

        # Route to correct provider
        if is_anthropic_model(model):
            return self._chat_anthropic(messages, model, temperature, max_tokens, response_format)
        else:
            return self._chat_openai(messages, model, temperature, max_tokens, response_format)

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        step_id = getattr(_tracking_context, "step_id", "unknown")
        wf_id = getattr(_tracking_context, "workflow_id", "")
        last_exc = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                choice = resp.choices[0]
                usage = resp.usage

                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0

                # ── Automatic cost tracking ──────────────────
                _log_usage(model, input_tokens, output_tokens)

                if attempt > 0:
                    logger.info(
                        "LLM call succeeded on attempt %d/%d (step=%s, wf=%s)",
                        attempt + 1, MAX_RETRIES + 1, step_id, wf_id,
                    )

                return {
                    "content": choice.message.content or "",
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                }

            except Exception as exc:
                last_exc = exc

                if not _is_retryable_error(exc) or attempt >= MAX_RETRIES:
                    logger.error(
                        "LLM call failed permanently (step=%s, wf=%s, attempt=%d/%d): %s",
                        step_id, wf_id, attempt + 1, MAX_RETRIES + 1, exc,
                    )
                    raise

                delay = _get_retry_delay(attempt, exc)
                logger.warning(
                    "LLM call failed (step=%s, wf=%s, attempt=%d/%d), "
                    "retrying in %.1fs: %s",
                    step_id, wf_id, attempt + 1, MAX_RETRIES + 1, delay, exc,
                )
                time.sleep(delay)

        # ── Anthropic fallback after all OpenAI retries exhausted ────────────
        # If the user has an Anthropic key configured, try the equivalent Claude
        # model. This keeps the platform up during OpenAI outages or rate limits.
        if self._anthropic_key and last_exc is not None and _is_retryable_error(last_exc):
            fallback_model = _OPENAI_TO_ANTHROPIC_FALLBACK.get(model)
            if fallback_model:
                logger.warning(
                    "OpenAI %s exhausted after %d retries — falling back to Anthropic %s "
                    "(step=%s, wf=%s): %s",
                    model, MAX_RETRIES + 1, fallback_model, step_id, wf_id, last_exc,
                )
                return self._chat_anthropic(
                    messages, fallback_model, temperature, max_tokens, response_format
                )

        raise last_exc  # type: ignore[misc]

    def _chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Call Anthropic Messages API.

        Converts from OpenAI message format (system in messages array)
        to Anthropic format (system as separate parameter).
        """
        client = self._get_anthropic()

        # Extract system messages and convert to Anthropic format
        system_parts = []
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        system_text = "\n\n".join(system_parts) if system_parts else ""

        # Anthropic requires alternating user/assistant messages.
        # Merge consecutive same-role messages if needed.
        merged_messages = []
        for msg in chat_messages:
            if merged_messages and merged_messages[-1]["role"] == msg["role"]:
                merged_messages[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged_messages.append(dict(msg))

        # Ensure first message is from user (Anthropic requirement)
        if merged_messages and merged_messages[0]["role"] != "user":
            merged_messages.insert(0, {
                "role": "user",
                "content": "Please continue.",
            })

        # If no messages at all, add a default
        if not merged_messages:
            merged_messages = [{"role": "user", "content": "Hello"}]

        # If response_format requires JSON, add instruction to system prompt
        if response_format and response_format.get("type") == "json_object":
            system_text += (
                "\n\nIMPORTANT: You MUST respond with valid JSON only. "
                "No markdown, no code fences, no text outside the JSON object."
            )

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": merged_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        step_id = getattr(_tracking_context, "step_id", "unknown")
        wf_id = getattr(_tracking_context, "workflow_id", "")
        last_exc = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = client.messages.create(**kwargs)

                # Extract content (Anthropic returns list of content blocks)
                content_text = ""
                for block in resp.content:
                    if hasattr(block, "text"):
                        content_text += block.text

                input_tokens = resp.usage.input_tokens if resp.usage else 0
                output_tokens = resp.usage.output_tokens if resp.usage else 0

                # ── Automatic cost tracking ──────────────────
                _log_usage(model, input_tokens, output_tokens)

                if attempt > 0:
                    logger.info(
                        "Anthropic call succeeded on attempt %d/%d (step=%s, wf=%s)",
                        attempt + 1, MAX_RETRIES + 1, step_id, wf_id,
                    )

                return {
                    "content": content_text,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                }

            except Exception as exc:
                last_exc = exc

                if not _is_retryable_error(exc) or attempt >= MAX_RETRIES:
                    logger.error(
                        "Anthropic call failed permanently (step=%s, wf=%s, attempt=%d/%d): %s",
                        step_id, wf_id, attempt + 1, MAX_RETRIES + 1, exc,
                    )
                    raise

                delay = _get_retry_delay(attempt, exc)
                logger.warning(
                    "Anthropic call failed (step=%s, wf=%s, attempt=%d/%d), "
                    "retrying in %.1fs: %s",
                    step_id, wf_id, attempt + 1, MAX_RETRIES + 1, delay, exc,
                )
                time.sleep(delay)

        raise last_exc  # type: ignore[misc]


class LLMResponseParseError(Exception):
    """Raised when an LLM response cannot be parsed as JSON."""

    def __init__(self, message: str, raw_content: str = ""):
        super().__init__(message)
        self.raw_content = raw_content


def parse_json_response(content: str) -> Any:
    """Parse LLM response as JSON with robust handling of edge cases.

    Handles:
    - Clean JSON
    - Markdown code fences (```json ... ```)
    - Multiple code fences (extracts first one)
    - Trailing text after JSON
    - Empty/whitespace responses
    - BOM characters
    """
    if not content or not content.strip():
        raise LLMResponseParseError(
            "LLM returned empty response", raw_content=content or ""
        )

    text = content.strip()

    # Remove BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]

    # Strategy 1: Direct parse (fastest path for clean JSON)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find the first { or [ and parse from there
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue
        # Find the matching closing bracket by scanning from the end
        end_idx = text.rfind(end_char)
        if end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # All strategies failed
    preview = text[:200] + ("..." if len(text) > 200 else "")
    raise LLMResponseParseError(
        "Could not parse LLM response as JSON. "
        "Tried direct parse, code fence extraction, and bracket matching. "
        "Preview: %s" % preview,
        raw_content=text,
    )


# ── Node safety wrapper ───────────────────────────────────────

class NodeError(Exception):
    """Raised when a pipeline node fails after exhausting retries."""

    def __init__(self, node_name: str, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.node_name = node_name
        self.original_error = original_error


def safe_node(func):
    """Decorator that wraps a pipeline node with error handling and timing.

    If the node function raises an exception:
    - Logs the error with full context (node name, workflow_id, duration)
    - Returns a degraded state with node_error info so the pipeline
      can decide whether to continue or abort
    - Never lets the raw exception propagate up to crash the pipeline
      (except for WorkflowBudgetExceeded, TokenCeilingExceeded,
      and LangGraph's GraphInterrupt which are intentional)
    """
    import functools

    # Import GraphInterrupt lazily to avoid hard dependency at module level
    try:
        from langgraph.errors import GraphInterrupt
        _passthrough_types = (WorkflowBudgetExceeded, TokenCeilingExceeded, DailyTokenCapExceeded, GraphInterrupt, KeyboardInterrupt)
    except ImportError:
        _passthrough_types = (WorkflowBudgetExceeded, TokenCeilingExceeded, DailyTokenCapExceeded, KeyboardInterrupt)

    @functools.wraps(func)
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        node_name = func.__name__
        wf_id = state.get("workflow_id", "unknown")
        start = time.time()

        try:
            result = func(state)
            elapsed = time.time() - start
            logger.info(
                "Node %s completed in %.1fs (wf=%s)",
                node_name, elapsed, wf_id,
            )
            return result

        except _passthrough_types:
            # These exceptions are intentional control flow, let them propagate
            raise

        except Exception as exc:
            elapsed = time.time() - start
            logger.error(
                "Node %s FAILED after %.1fs (wf=%s): %s",
                node_name, elapsed, wf_id, exc,
                exc_info=True,
            )
            return {
                "current_step": node_name,
                "node_error": {
                    "node": node_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "elapsed_seconds": round(elapsed, 2),
                },
            }

    return wrapper


# Default client, overridden in tests
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the LLM client. Returns OpenAIClient by default."""
    global _default_client
    if _default_client is not None:
        return _default_client
    return OpenAIClient()


def set_llm_client(client: Optional[LLMClient]) -> None:
    """Override the default LLM client (for testing)."""
    global _default_client
    _default_client = client
