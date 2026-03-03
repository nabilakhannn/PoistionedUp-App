"""SDK Agent Layer: direct Python wrappers for agent tasks.

Provides fully-controlled, programmatic agent task execution using the
existing LLM client (OpenAI + Anthropic routing, cost tracking, retries,
model fallback). Unlike OpenClaw SOUL.md agents, these give you:

  - Explicit data flow (you choose exactly what goes in and out)
  - Per-task model selection (copywriter gets gpt-4o, QA gets haiku)
  - Synchronous execution with full error handling
  - No WebSocket timeouts — runs in-process with the FastAPI request

OpenClaw is still used for Telegram / Mission Control UI / chat sessions.
This layer handles ad creative, QA, research synthesis, and repurposing
that need programmatic control.

Usage example:
    result = run_copywriter_task(
        prompt="Write a LinkedIn hook about productivity...",
        brand_context="Bold, direct, results-oriented coach for tech leaders.",
    )
    if result.success:
        print(result.content)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from worker.graph.llm import get_llm_client, parse_json_response, LLMResponseParseError

logger = logging.getLogger("app.services.sdk_agents")


# ── Result dataclass ─────────────────────────────────────────────────────


@dataclass
class AgentResult:
    """Structured result from an SDK agent task."""
    success: bool
    content: str
    parsed: Optional[Dict[str, Any]] = None  # JSON-parsed content if applicable
    error: Optional[str] = None
    model_used: str = ""
    tokens_used: int = 0
    fallback_used: bool = False  # True when Anthropic was used instead of OpenAI


# ── Internal helpers ─────────────────────────────────────────────────────


def _run_task(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    expect_json: bool = False,
) -> AgentResult:
    """Internal: single LLM call with full error handling and cost tracking.

    Uses the shared LLM client (OpenAI + Anthropic routing, retries, fallback).
    """
    llm = get_llm_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response_format = {"type": "json_object"} if expect_json else None

    try:
        resp = llm.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        content = resp.get("content", "")
        usage = resp.get("usage", {})
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        parsed = None
        if expect_json and content:
            try:
                parsed = parse_json_response(content)
            except LLMResponseParseError as e:
                logger.warning("SDK agent JSON parse failed: %s", e)

        return AgentResult(
            success=True,
            content=content,
            parsed=parsed,
            model_used=model,
            tokens_used=tokens,
        )

    except Exception as exc:
        logger.error("SDK agent task failed (model=%s): %s", model, exc)
        return AgentResult(
            success=False,
            content="",
            error=str(exc),
            model_used=model,
        )


# ── Public task functions ────────────────────────────────────────────────


def run_copywriter_task(
    prompt: str,
    brand_context: str = "",
    model: str = "gpt-4o",
    user_id: str = "",
    brand_id: str = "",
    use_tool_use: bool = False,
) -> AgentResult:
    """Run a copywriting task.

    When use_tool_use=True and user_id is provided, delegates to the multi-step
    tool-use agent (Claude Sonnet 4.6 with read_playbook + fetch_brand_profile tools).
    Otherwise falls back to the single-call path for backwards compatibility.

    Args:
        prompt: The content/copy request (e.g. "Write a LinkedIn hook about...").
        brand_context: Brand positioning, tone, and voice summary.
        model: Model override (ignored when use_tool_use=True).
        user_id: Supabase user ID (required for tool-use path).
        brand_id: Optional brand UUID for brand profile lookup.
        use_tool_use: If True and user_id set, uses multi-step Claude tool-use loop.

    Returns:
        AgentResult with the generated copy in `content`.
    """
    if use_tool_use and user_id:
        from app.services.tool_use_agents import run_tool_use_agent, WRITING_MODEL
        system_prompt = (
            "You are a world-class direct-response copywriter specializing in personal branding. "
            "Write punchy, authentic, engaging copy that sounds human and drives action. "
            "Do not use em dashes, semicolons, or AI-tell phrases like 'It's worth noting'. "
            "Keep sentences short. Start with a strong hook.\n\n"
            "Start by reading your playbook with read_playbook('copywriter', user_id). "
            "If a brand_id is in the prompt, fetch the brand profile. "
            "Then write the copy. Run score_content_quality on your draft before delivering."
        )
        if brand_context:
            system_prompt += f"\n\nAdditional brand context:\n{brand_context}"
        return run_tool_use_agent(
            agent_id="copywriter",
            task_type="copywriting",
            system_prompt=system_prompt,
            user_prompt=prompt,
            user_id=user_id,
            brand_id=brand_id or None,
            available_tools=["read_playbook", "fetch_brand_profile", "score_content_quality"],
            model=WRITING_MODEL,
            temperature=0.8,
        )

    # Single-call fallback (backwards compatible)
    system_prompt = (
        "You are a world-class direct-response copywriter specializing in personal branding. "
        "Write punchy, authentic, engaging copy that sounds human and drives action. "
        "Do not use em dashes, semicolons, or AI-tell phrases like 'It's worth noting'. "
        "Keep sentences short. Start with a strong hook."
    )
    if brand_context:
        system_prompt += f"\n\nBrand context:\n{brand_context}"

    return _run_task(
        system_prompt=system_prompt,
        user_prompt=prompt,
        model=model,
        temperature=0.8,
        max_tokens=1500,
    )


def run_qa_task(
    content: str,
    criteria: str = "",
    model: str = "claude-haiku-4-5-20251001",
) -> AgentResult:
    """Run a QA review task using direct SDK call.

    Fast and cheap — defaults to Claude Haiku for cost efficiency.

    Args:
        content: The content text to review.
        criteria: Optional evaluation criteria or rubric.
        model: Model to use. Defaults to claude-haiku for speed + cost.

    Returns:
        AgentResult with JSON-parsed scores in `parsed`.
    """
    system_prompt = (
        "You are a content quality reviewer. Evaluate the provided content and return a JSON "
        "object with scores (0-100) for: voice_authenticity, hook_strength, clarity, "
        "ai_detection_risk, overall. Include a brief feedback string for each dimension."
    )
    if criteria:
        system_prompt += f"\n\nEvaluation criteria:\n{criteria}"

    return _run_task(
        system_prompt=system_prompt,
        user_prompt=f"Review this content:\n\n{content[:8000]}",
        model=model,
        temperature=0.2,
        max_tokens=800,
        expect_json=True,
    )


def run_research_synthesis_task(
    research_data: str,
    synthesis_goal: str,
    model: str = "gpt-4o",
    user_id: str = "",
    brand_id: str = "",
    use_tool_use: bool = False,
) -> AgentResult:
    """Synthesize web research data into structured insights.

    When use_tool_use=True and user_id is provided, delegates to the multi-step
    tool-use agent (Claude Sonnet 4.6 with web_search + synthesize_research tools).
    Research is done via Perplexity (real-time web) and Gemini (synthesis).
    Otherwise falls back to the single-call path.

    Args:
        research_data: Raw research text or query to investigate.
        synthesis_goal: What to extract/synthesize from the data.
        model: Model override (ignored when use_tool_use=True).
        user_id: Supabase user ID (required for tool-use path).
        brand_id: Optional brand UUID.
        use_tool_use: If True and user_id set, uses multi-step tool-use loop.

    Returns:
        AgentResult with synthesized insights in `content`.
    """
    if use_tool_use and user_id:
        from app.services.tool_use_agents import run_tool_use_agent, WRITING_MODEL
        system_prompt = (
            "You are a research analyst specializing in personal branding and content strategy. "
            "Use web_search to find current, relevant information. "
            "Use synthesize_research to combine multiple sources into structured insights. "
            "Be specific, cite patterns, and surface actionable opportunities. "
            "No generic observations."
        )
        user_prompt = (
            f"Research goal: {synthesis_goal}\n\n"
            f"Starting data (supplement with web search):\n{research_data[:3000]}"
        )
        return run_tool_use_agent(
            agent_id="trend-analyzer",
            task_type="research_synthesis",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            user_id=user_id,
            brand_id=brand_id or None,
            available_tools=["web_search", "synthesize_research", "fetch_brand_profile"],
            model=WRITING_MODEL,
            temperature=0.3,
        )

    # Single-call fallback
    system_prompt = (
        "You are a research analyst. Synthesize the provided data into clear, actionable insights. "
        "Focus on patterns, opportunities, and evidence-backed conclusions. "
        "Be concise and specific — no generic observations."
    )

    user_prompt = (
        f"Goal: {synthesis_goal}\n\n"
        f"Research data:\n{research_data[:12000]}"
    )

    return _run_task(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=0.3,
        max_tokens=2000,
    )
