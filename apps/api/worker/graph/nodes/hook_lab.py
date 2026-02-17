"""Node 4: Hook lab — generate 7 hooks, then interrupt for user selection."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from langgraph.types import interrupt

from worker.graph.llm import get_llm_client, parse_json_response, set_tracking_context
from worker.graph.prompts import hook_lab as prompts

logger = logging.getLogger("worker.graph.nodes.hook_lab")


def _fetch_memory_context(user_id: str, context_query: str = "") -> str:
    """Fetch agent memories for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(user_id, context_query or "hooks and content openings", limit=10)
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


def hook_lab(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate 7 hook candidates, then pause for user to pick one."""
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "hook_lab")

    topic = state.get("selected_topic", {})
    profile = state.get("profile_snapshot", {})

    # Fetch performance context (top hooks / anti-hooks for this user)
    user_id = state.get("user_id", "")
    perf_context = _fetch_performance_context(user_id)

    # Fetch agent memory context (hook preferences the agent has learned)
    topic_title = topic.get("title", "")
    memory_context = _fetch_memory_context(user_id, f"hooks for {topic_title}")

    # Build system prompt with optional context layers
    system_prompt = prompts.SYSTEM
    if perf_context:
        system_prompt += "\n\n" + perf_context
    if memory_context:
        system_prompt += "\n\n" + memory_context

    # Fetch experiment context (active A/B tests affecting hooks)
    exp_context = _fetch_experiment_context(user_id)
    if exp_context:
        system_prompt += "\n\n" + exp_context

    llm = get_llm_client()
    resp = llm.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompts.USER.format(
                topic_title=topic.get("title", ""),
                audience_pain=topic.get("audience_pain", ""),
                why_now=topic.get("why_now", ""),
                novelty_angle=topic.get("novelty_angle", ""),
                profile=json.dumps(profile, indent=2),
            )},
        ],
        model="gpt-4o",
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(resp["content"])
    hooks = result.get("hook_candidates", [])

    # Sort by total_score descending
    hooks.sort(key=lambda h: h.get("total_score", 0), reverse=True)

    logger.info(
        "hook_lab: generated %d hooks, top score=%d",
        len(hooks),
        hooks[0].get("total_score", 0) if hooks else 0,
    )

    # Now interrupt for user selection
    user_selection = interrupt({
        "type": "hook_selection",
        "hook_candidates": hooks,
        "topic": topic,
    })

    selected_id = user_selection.get("selected_hook_id", "")
    selected_hook = None

    for hook in hooks:
        if hook.get("id") == selected_id:
            selected_hook = hook
            break

    if selected_hook is None and hooks:
        selected_hook = hooks[0]
        logger.warning(
            "hook_lab: selected_id=%s not found, using top hook",
            selected_id,
        )

    logger.info(
        "hook_lab: user selected hook type=%s",
        selected_hook.get("hook_type", "unknown") if selected_hook else "none",
    )

    return {
        "hook_candidates": hooks,
        "selected_hook": selected_hook,
        "current_step": "hook_lab",
    }
