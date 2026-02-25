"""Node 2: Gap analysis — generate 10 scored topic candidates."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from worker.graph.context import fetch_relevant_resources as _fetch_relevant_resources
from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response, set_tracking_context, safe_node
from worker.graph.nodes.signal_research import _format_ica, _format_offer
from worker.graph.prompts import gap_analysis as prompts

logger = logging.getLogger("worker.graph.nodes.gap_analysis")


def _fetch_memory_context(user_id: str, context_query: str = "") -> str:
    """Fetch agent memories for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(user_id, context_query or "content topics and gaps", limit=10)
        return format_memories_as_context(memories)
    except Exception as e:
        logger.debug("Memory context unavailable: %s", e)
        return ""


def _fetch_experiment_context(user_id: str, platform: str = "") -> str:
    """Fetch active experiment context for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.experiments import get_active_experiment_context
        return get_active_experiment_context(user_id, platform=platform)
    except Exception as e:
        logger.debug("Experiment context unavailable: %s", e)
        return ""


def _fetch_performance_context(user_id: str, platform: str = "") -> str:
    """Fetch performance data for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        resp = (
            admin.table("content_posts")
            .select("*")
            .eq("user_id", user_id)
            .order("published_at", desc=True)
            .execute()
        )
        posts = resp.data if resp.data else []
        if not posts:
            return ""
        from app.services.performance_analytics import get_performance_context
        return get_performance_context(posts, platform=platform)
    except Exception as e:
        logger.debug("Performance context unavailable: %s", e)
        return ""


@safe_node
def gap_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze gaps and generate 10 topic candidates with scores."""
    _tier = state.get("settings", {}).get("model_tier", "")
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "gap_analysis", _tier)

    goal_text = state["goal_text"]
    profile = state.get("profile_snapshot", {})
    signals = state.get("research_signals", [])

    # Fetch relevant resources via semantic search
    user_id = state.get("user_id", "")
    gold_resources = _fetch_relevant_resources(goal_text, user_id)

    # Fetch performance context (what's worked before for this user)
    perf_context = _fetch_performance_context(user_id)

    # Fetch agent memory context (what the agent has learned)
    memory_context = _fetch_memory_context(user_id, goal_text)

    # Build system prompt with optional context layers
    system_prompt = prompts.SYSTEM
    if perf_context:
        system_prompt += "\n\n" + perf_context
    if memory_context:
        system_prompt += "\n\n" + memory_context

    # Fetch experiment context (active A/B tests)
    exp_context = _fetch_experiment_context(user_id)
    if exp_context:
        system_prompt += "\n\n" + exp_context

    llm = get_llm_client()
    resp = llm.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompts.USER.format(
                goal_text=goal_text,
                profile=json.dumps(profile, indent=2),
                ica_context=_format_ica(profile),
                offer_context=_format_offer(profile),
                signals=json.dumps(signals, indent=2),
                gold_resources=gold_resources,
            )},
        ],
        model=get_model_for_step("gap_analysis"),
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(resp["content"])
    candidates = result.get("topic_candidates", [])

    # Sort by opportunity_score descending
    candidates.sort(key=lambda t: t.get("opportunity_score", 0), reverse=True)

    logger.info(
        "gap_analysis: generated %d topic candidates, top score=%d",
        len(candidates),
        candidates[0].get("opportunity_score", 0) if candidates else 0,
    )

    return {
        "topic_candidates": candidates,
        "current_step": "gap_analysis_topic_candidates",
    }
