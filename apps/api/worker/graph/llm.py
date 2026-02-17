"""LLM client wrapper for pipeline nodes.

Provides a mockable interface so pipeline tests can run without
hitting the real OpenAI API. In production, calls OpenAI's chat
completions endpoint.

Includes automatic cost tracking (writes to usage_costs table)
and per-step token ceiling enforcement.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, List, Optional, Protocol

from app.config import settings

logger = logging.getLogger("worker.graph.llm")


# ── Cost estimation (USD per 1K tokens, GPT-4o pricing) ─────
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

# ── Model routing per pipeline step ─────────────────────────
# Creative steps use GPT-4o (best quality for generation)
# Checking steps use GPT-4o-mini (cheaper, fast, good enough for review)
MODEL_FOR_STEP = {
    "signal_research": "gpt-4o",
    "gap_analysis": "gpt-4o",
    "topic_selection": "gpt-4o",
    "hook_lab": "gpt-4o",
    "script_generation": "gpt-4o",
    "editor": "gpt-4o-mini",
    "testing": "gpt-4o-mini",
    "approval": "gpt-4o-mini",
    # Brand chat and other services default to gpt-4o
}


def get_model_for_step(step_id: str = "") -> str:
    """Get the appropriate model for a given pipeline step.

    If no step is provided, uses the current tracking context step.
    Falls back to gpt-4o if step is unknown.
    """
    if not step_id:
        step_id = getattr(_tracking_context, "step_id", "") or ""
    return MODEL_FOR_STEP.get(step_id, "gpt-4o")


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o"])
    return (input_tokens / 1000.0 * pricing["input"]) + (
        output_tokens / 1000.0 * pricing["output"]
    )


# ── Thread-local context for cost tracking ───────────────────
_tracking_context = threading.local()


def set_tracking_context(
    workflow_id: str, user_id: str, step_id: str
) -> None:
    """Set the context for cost tracking. Called by each pipeline node."""
    _tracking_context.workflow_id = workflow_id
    _tracking_context.user_id = user_id
    _tracking_context.step_id = step_id


def clear_tracking_context() -> None:
    """Clear the tracking context after a node completes."""
    _tracking_context.workflow_id = None
    _tracking_context.user_id = None
    _tracking_context.step_id = None


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


class OpenAIClient:
    """Real OpenAI client for production use.

    Automatically logs cost to usage_costs and checks token ceilings.
    """

    def __init__(self, api_key: Optional[str] = None):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key or settings.openai_api_key)

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

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage = resp.usage

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        # ── Automatic cost tracking ──────────────────────────
        _log_usage(model, input_tokens, output_tokens)

        return {
            "content": choice.message.content or "",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        }


def parse_json_response(content: str) -> Any:
    """Parse LLM response as JSON, handling markdown code fences."""
    text = content.strip()
    if text.startswith("```"):
        # Remove opening fence (possibly ```json)
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
    return json.loads(text)


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
