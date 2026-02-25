"""Proactive Advisor — surfaces actionable suggestions based on compound learning.

Aggregates signals from performance analytics, agent memory, experiments,
and content history to generate specific, timely recommendations the user
can act on right away.

Key function:
  - get_suggestions() — returns a list of ranked advisor suggestions
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("app.services.advisor")


def get_suggestions(
    user_id: str,
    brand_id: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Generate proactive advisor suggestions for the user.

    Pulls data from multiple sources, builds a context snapshot,
    then asks the LLM to propose actionable next steps.

    Returns list of suggestion dicts with keys:
      - title: short headline
      - body: 1-2 sentence explanation
      - category: one of performance, content, experiment, voice, schedule
      - priority: high / medium / low
      - action_type: optional CTA hint (create_content, run_experiment, etc.)
    """
    from app.deps import get_admin_client

    admin = get_admin_client()

    # ── Gather signals in parallel-ish (sequential but fast DB queries) ──

    signals = {}

    # 1. Recent performance patterns
    signals["performance"] = _get_performance_signals(admin, user_id, brand_id)

    # 2. Active memories (lessons + preferences)
    signals["memories"] = _get_memory_signals(admin, user_id, brand_id)

    # 3. Experiment state
    signals["experiments"] = _get_experiment_signals(admin, user_id, brand_id)

    # 4. Content cadence (how long since last content)
    signals["cadence"] = _get_cadence_signals(admin, user_id, brand_id)

    # 5. Schedule gaps
    signals["schedule"] = _get_schedule_signals(admin, user_id, brand_id)

    # Check if we have enough data for LLM suggestions
    has_data = any(
        signals[k] and signals[k].get("has_data", False)
        for k in signals
    )

    if not has_data:
        return _get_cold_start_suggestions()

    # ── Ask LLM for suggestions ──
    try:
        suggestions = _generate_suggestions_via_llm(signals, limit)
    except Exception as e:
        logger.warning("LLM suggestion generation failed: %s", e)
        suggestions = _get_rule_based_suggestions(signals)

    return suggestions[:limit]


# ── Signal gatherers ────────────────────────────────────────


def _get_performance_signals(
    admin, user_id: str, brand_id: Optional[str]
) -> Dict[str, Any]:
    """Pull recent performance patterns."""
    query = (
        admin.table("content_posts")
        .select("platform, hook_type, topic, engagement_rate, views, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    posts = resp.data or []

    if not posts:
        return {"has_data": False}

    # Calculate averages
    rates = [p["engagement_rate"] for p in posts if p.get("engagement_rate")]
    avg_rate = sum(rates) / len(rates) if rates else 0

    # Find best performing hook types
    hook_perf = {}
    for p in posts:
        ht = p.get("hook_type", "unknown")
        if p.get("engagement_rate"):
            hook_perf.setdefault(ht, []).append(p["engagement_rate"])

    best_hooks = []
    for ht, rates_list in hook_perf.items():
        avg = sum(rates_list) / len(rates_list)
        best_hooks.append({"hook_type": ht, "avg_rate": round(avg, 4), "count": len(rates_list)})
    best_hooks.sort(key=lambda x: x["avg_rate"], reverse=True)

    # Find top topics
    topic_perf = {}
    for p in posts:
        t = p.get("topic", "")
        if t and p.get("engagement_rate"):
            topic_perf.setdefault(t, []).append(p["engagement_rate"])

    top_topics = []
    for t, rates_list in topic_perf.items():
        avg = sum(rates_list) / len(rates_list)
        top_topics.append({"topic": t, "avg_rate": round(avg, 4), "count": len(rates_list)})
    top_topics.sort(key=lambda x: x["avg_rate"], reverse=True)

    return {
        "has_data": True,
        "total_posts": len(posts),
        "avg_engagement_rate": round(avg_rate, 4),
        "best_hooks": best_hooks[:3],
        "top_topics": top_topics[:3],
    }


def _get_memory_signals(
    admin, user_id: str, brand_id: Optional[str]
) -> Dict[str, Any]:
    """Pull recent active memories."""
    query = (
        admin.table("agent_memory")
        .select("memory_type, content, confidence, category, created_at")
        .eq("user_id", user_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(10)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    memories = resp.data or []

    if not memories:
        return {"has_data": False}

    lessons = [m for m in memories if m["memory_type"] == "lesson"]
    preferences = [m for m in memories if m["memory_type"] == "preference"]
    patterns = [m for m in memories if m["memory_type"] == "content_pattern"]

    return {
        "has_data": True,
        "lesson_count": len(lessons),
        "preference_count": len(preferences),
        "pattern_count": len(patterns),
        "recent_lessons": [m["content"] for m in lessons[:3]],
        "recent_preferences": [m["content"] for m in preferences[:3]],
    }


def _get_experiment_signals(
    admin, user_id: str, brand_id: Optional[str]
) -> Dict[str, Any]:
    """Pull experiment state."""
    query = (
        admin.table("agent_experiments")
        .select("status, variable, hypothesis, winner, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(10)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    experiments = resp.data or []

    if not experiments:
        return {"has_data": False}

    active = [e for e in experiments if e["status"] == "active"]
    completed = [e for e in experiments if e["status"] == "completed"]
    proposed = [e for e in experiments if e["status"] == "proposed"]

    return {
        "has_data": True,
        "active_count": len(active),
        "completed_count": len(completed),
        "proposed_count": len(proposed),
        "active_hypotheses": [e["hypothesis"] for e in active[:2]],
        "recent_winners": [
            {"type": e["variable"], "winner": e.get("winner")}
            for e in completed[:2]
            if e.get("winner")
        ],
    }


def _get_cadence_signals(
    admin, user_id: str, brand_id: Optional[str]
) -> Dict[str, Any]:
    """Check content creation cadence."""
    query = (
        admin.table("workflows")
        .select("created_at, status")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    workflows = resp.data or []

    if not workflows:
        return {"has_data": False}

    last_created = workflows[0]["created_at"]
    try:
        last_dt = datetime.fromisoformat(last_created.replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - last_dt).days
    except Exception:
        days_since = 0

    approved_count = len([w for w in workflows if w["status"] == "approved"])

    return {
        "has_data": True,
        "days_since_last_content": days_since,
        "recent_workflow_count": len(workflows),
        "approved_count": approved_count,
    }


def _get_schedule_signals(
    admin, user_id: str, brand_id: Optional[str]
) -> Dict[str, Any]:
    """Check schedule for gaps."""
    now_iso = datetime.now(timezone.utc).isoformat()

    query = (
        admin.table("scheduled_items")
        .select("scheduled_at, status")
        .eq("user_id", user_id)
        .gte("scheduled_at", now_iso)
        .order("scheduled_at", desc=False)
        .limit(7)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    upcoming = resp.data or []

    return {
        "has_data": True if upcoming else False,
        "upcoming_count": len(upcoming),
        "next_scheduled": upcoming[0]["scheduled_at"] if upcoming else None,
    }


# ── LLM-based suggestion generation ────────────────────────


def _generate_suggestions_via_llm(
    signals: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    """Use GPT to generate actionable suggestions from aggregated signals."""
    from openai import OpenAI
    from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

    client = OpenAI(api_key=settings.openai_api_key)

    system_prompt = f"""You are a content strategy advisor for a personal brand creator.
You receive a data snapshot of the user's recent performance, memories, experiments,
content cadence, and schedule. Your job is to generate {limit} specific, actionable
suggestions the user can act on TODAY.

Rules for suggestions:
- Be specific. Reference actual data (hook types, engagement rates, topic names)
- Each suggestion must have a clear action the user can take
- Prioritize based on impact: what will move the needle most?
- Categories: performance, content, experiment, voice, schedule
- Priority levels: high (act now), medium (this week), low (nice to have)
- action_type options: create_content, run_experiment, review_performance,
  update_schedule, analyze_voice, review_memory

{HUMAN_WRITING_RULES}

Return ONLY valid JSON array. Each item has:
  title (string, max 60 chars)
  body (string, 1-2 sentences, max 200 chars)
  category (string)
  priority (string: high/medium/low)
  action_type (string)

Do NOT wrap in markdown code fences. Return raw JSON array."""

    user_msg = f"Here is my current data snapshot:\n\n{json.dumps(signals, indent=2, default=str)}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=1200,
    )

    raw = resp.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines)

    suggestions = json.loads(raw)

    if not isinstance(suggestions, list):
        logger.warning("LLM returned non-list suggestions")
        return []

    # Validate structure
    valid = []
    for s in suggestions:
        if isinstance(s, dict) and "title" in s and "body" in s:
            valid.append({
                "title": str(s.get("title", ""))[:60],
                "body": str(s.get("body", ""))[:200],
                "category": str(s.get("category", "content")),
                "priority": str(s.get("priority", "medium")),
                "action_type": str(s.get("action_type", "")),
            })

    return valid


# ── Rule-based fallback ─────────────────────────────────────


def _get_rule_based_suggestions(
    signals: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate basic suggestions from rules when LLM fails."""
    suggestions = []

    perf = signals.get("performance", {})
    cadence = signals.get("cadence", {})
    schedule = signals.get("schedule", {})
    experiments = signals.get("experiments", {})

    # Cadence alert
    days = cadence.get("days_since_last_content", 0)
    if days >= 7:
        suggestions.append({
            "title": f"You haven't created content in {days} days",
            "body": "Consistency matters more than perfection. Start a new workflow today with a topic you've been thinking about.",
            "category": "content",
            "priority": "high",
            "action_type": "create_content",
        })

    # Empty schedule
    if schedule.get("has_data") and schedule.get("upcoming_count", 0) == 0:
        suggestions.append({
            "title": "Your schedule is empty",
            "body": "No upcoming content scheduled. Move an approved piece to your calendar to stay visible.",
            "category": "schedule",
            "priority": "high",
            "action_type": "update_schedule",
        })

    # Best hook type
    best_hooks = perf.get("best_hooks", [])
    if best_hooks:
        top = best_hooks[0]
        suggestions.append({
            "title": f"Your {top['hook_type']} hooks perform best",
            "body": f"Average {top['avg_rate']:.1%} engagement across {top['count']} posts. Use this style in your next piece.",
            "category": "performance",
            "priority": "medium",
            "action_type": "create_content",
        })

    # Pending experiments
    proposed = experiments.get("proposed_count", 0)
    if proposed > 0:
        suggestions.append({
            "title": f"{proposed} experiment(s) waiting for approval",
            "body": "Review proposed experiments and activate one to start learning what works for your audience.",
            "category": "experiment",
            "priority": "medium",
            "action_type": "run_experiment",
        })

    # Performance review prompt
    total_posts = perf.get("total_posts", 0)
    if total_posts >= 5:
        suggestions.append({
            "title": "Time for a performance review",
            "body": f"You have {total_posts} tracked posts. Review your analytics to spot trends and double down on winners.",
            "category": "performance",
            "priority": "low",
            "action_type": "review_performance",
        })

    return suggestions


def _get_cold_start_suggestions() -> List[Dict[str, Any]]:
    """Return starter suggestions when user has no data yet."""
    return [
        {
            "title": "Create your first piece of content",
            "body": "Start a new workflow to generate your first content pack. The AI will learn from every piece you create.",
            "category": "content",
            "priority": "high",
            "action_type": "create_content",
        },
        {
            "title": "Complete your brand profile",
            "body": "A stronger brand profile gives the AI better context. Fill out more modules to improve content quality.",
            "category": "content",
            "priority": "medium",
            "action_type": "",
        },
    ]
