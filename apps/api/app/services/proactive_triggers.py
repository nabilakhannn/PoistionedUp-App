"""Proactive Jumbo Triggers — Slice 102 (Fix G).

Checks 7 conditions every 60 min and surfaces suggestions as floating Jumbo
cards in the UI. Called from GET /agent-api/suggestions (user-facing).

All checks are read-only, stateless, and fail silently.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("app.services.proactive_triggers")


def get_suggestions(user_id: str, brand_id: Optional[str] = None) -> list[dict]:
    """Return proactive suggestions for the user.

    Each suggestion: { id, priority, title, body, action_url, cta, trigger_type }

    Priority: "urgent" | "high" | "normal"
    """
    from app.deps import get_admin_client
    sb = get_admin_client()
    suggestions: list[dict] = []
    now = datetime.now(timezone.utc)

    # ── Resolve brand_id ──────────────────────────────────────────────────
    if not brand_id:
        try:
            brand_resp = (
                sb.table("personal_brands")
                .select("id")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if brand_resp.data:
                brand_id = brand_resp.data[0]["id"]
        except Exception:
            pass

    if not brand_id:
        return []

    # ── Trigger 1: No approved post in 48h ──────────────────────────────
    try:
        cutoff_48h = (now - timedelta(hours=48)).isoformat()
        last_post = (
            sb.table("agent_deliverables")
            .select("created_at")
            .eq("user_id", user_id)
            .eq("status", "approved")
            .gte("created_at", cutoff_48h)
            .limit(1)
            .execute()
        )
        if not last_post.data:
            # Count pending in queue
            pending = (
                sb.table("agent_deliverables")
                .select("id")
                .eq("user_id", user_id)
                .eq("status", "review")
                .execute()
            )
            pending_count = len(pending.data or [])
            body = (
                f"You haven't published in over 48 hours. "
                f"{f'{pending_count} post(s) are waiting for your approval.' if pending_count else 'Run the pipeline to generate new content.'}"
            )
            suggestions.append({
                "id": "no_post_48h",
                "priority": "high",
                "trigger_type": "posting_gap",
                "title": "You haven't posted in 2 days",
                "body": body,
                "action_url": "/mission-control",
                "cta": "Review Queue" if pending_count else "Run Pipeline",
            })
    except Exception as exc:
        logger.warning("Trigger 1 failed user=%s: %s", user_id, exc)

    # ── Trigger 2: No journal entry in 3 days ───────────────────────────
    try:
        cutoff_72h = (now - timedelta(hours=72)).isoformat()
        last_journal = (
            sb.table("experience_journal")
            .select("created_at")
            .eq("user_id", user_id)
            .gte("created_at", cutoff_72h)
            .limit(1)
            .execute()
        )
        if not last_journal.data:
            suggestions.append({
                "id": "no_journal_3d",
                "priority": "normal",
                "trigger_type": "content_quality",
                "title": "Add a journal entry — content gets generic without real stories",
                "body": "Drop a quick note about a recent client win, call insight, or learning. I'll turn it into 3 grounded posts.",
                "action_url": "/intelligence",
                "cta": "Add Entry",
            })
    except Exception as exc:
        logger.warning("Trigger 2 failed user=%s: %s", user_id, exc)

    # ── Trigger 3: Last 3 posts same hook type ───────────────────────────
    try:
        last_posts = (
            sb.table("agent_deliverables")
            .select("content")
            .eq("user_id", user_id)
            .eq("status", "approved")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        if last_posts.data and len(last_posts.data) >= 3:
            # Check if all 3 start with a question (same hook pattern)
            starts_with_q = sum(
                1 for d in last_posts.data
                if str(d.get("content", "")).strip().startswith(("Are ", "Do ", "Have ", "Is ", "Can ", "Did ", "What ", "Why ", "How "))
            )
            if starts_with_q >= 3:
                suggestions.append({
                    "id": "same_hook_type",
                    "priority": "normal",
                    "trigger_type": "content_variety",
                    "title": "Your last 3 posts all used question hooks",
                    "body": "Switching hook style — your audience needs variety. Try a bold claim or story opener next.",
                    "action_url": "/studio/hooks",
                    "cta": "View Hook Library",
                })
    except Exception as exc:
        logger.warning("Trigger 3 failed user=%s: %s", user_id, exc)

    # ── Trigger 4: Competitor threat > 70 with no response ───────────────
    try:
        high_threats = (
            sb.table("competitors")
            .select("id, name, threat_score")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .gte("threat_score", 70)
            .limit(1)
            .execute()
        )
        if high_threats.data:
            comp = high_threats.data[0]
            suggestions.append({
                "id": f"competitor_threat_{comp['id']}",
                "priority": "high",
                "trigger_type": "competitive",
                "title": f"{comp['name']} is a threat (score: {comp['threat_score']}/100)",
                "body": "They're gaining traction in your niche. Want me to draft a response post that positions you against their approach?",
                "action_url": f"/mission-control/competitors/{comp['id']}",
                "cta": "View Competitor",
            })
    except Exception as exc:
        logger.warning("Trigger 4 failed user=%s: %s", user_id, exc)

    # ── Trigger 5: Pending approvals > 2 days old ─────────────────────────
    try:
        cutoff_48h_b = (now - timedelta(hours=48)).isoformat()
        stale_approvals = (
            sb.table("agent_deliverables")
            .select("id, title, created_at")
            .eq("user_id", user_id)
            .eq("status", "review")
            .lte("created_at", cutoff_48h_b)
            .execute()
        )
        if stale_approvals.data and len(stale_approvals.data) >= 1:
            count = len(stale_approvals.data)
            suggestions.append({
                "id": "stale_approvals",
                "priority": "urgent",
                "trigger_type": "approval_needed",
                "title": f"{count} post{'s' if count > 1 else ''} waiting 48h+ for your approval",
                "body": "These posts were written and are ready — they'll never publish without your OK. Takes 30 seconds.",
                "action_url": "/mission-control",
                "cta": f"Approve {count} Post{'s' if count > 1 else ''}",
            })
    except Exception as exc:
        logger.warning("Trigger 5 failed user=%s: %s", user_id, exc)

    # ── Trigger 6: Leads need review ─────────────────────────────────────
    try:
        new_leads = (
            sb.table("leads")
            .select("id")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .eq("status", "new")
            .execute()
        )
        if new_leads.data and len(new_leads.data) >= 3:
            count = len(new_leads.data)
            suggestions.append({
                "id": "new_leads",
                "priority": "high",
                "trigger_type": "sales",
                "title": f"{count} new ICP leads waiting for review",
                "body": "Your Apollo filters found new matches. Review and start outreach sequences before they go cold.",
                "action_url": "/sales",
                "cta": "Review Leads",
            })
    except Exception as exc:
        logger.warning("Trigger 6 failed user=%s: %s", user_id, exc)

    # ── Trigger 7: Low QA avg this week ──────────────────────────────────
    try:
        week_ago = (now - timedelta(days=7)).isoformat()
        week_posts = (
            sb.table("agent_deliverables")
            .select("qa_score")
            .eq("user_id", user_id)
            .gte("created_at", week_ago)
            .not_.is_("qa_score", "null")
            .execute()
        )
        if week_posts.data and len(week_posts.data) >= 3:
            scores = [d["qa_score"] for d in week_posts.data if d.get("qa_score")]
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score < 75:
                suggestions.append({
                    "id": "low_qa_avg",
                    "priority": "normal",
                    "trigger_type": "quality",
                    "title": f"Content quality dropped this week (avg: {avg_score:.0f}/100)",
                    "body": "Main issue: posts are too generic. Add journal entries and power words to your brand profile to fix this.",
                    "action_url": "/intelligence",
                    "cta": "Add Journal Entry",
                })
    except Exception as exc:
        logger.warning("Trigger 7 failed user=%s: %s", user_id, exc)

    # ── Trigger 8: No story bank material in 7 days ────────────────
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_stories = (
            sb.table("experience_journal")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", week_ago)
            .limit(1)
            .execute()
        )
        if (recent_stories.count or 0) == 0:
            suggestions.append({
                "id": "no_recent_stories",
                "priority": "normal",
                "trigger_type": "engagement",
                "title": "Add fresh material to your Story Bank",
                "body": "Your AI agents write better when they have real stories. "
                        "Drop a recent win, insight, or opinion. Takes 30 seconds.",
                "action_url": "/content/stories",
                "cta": "Add Material",
            })
    except Exception as exc:
        logger.warning("Trigger 8 failed user=%s: %s", user_id, exc)

    # Sort: urgent → high → normal
    priority_order = {"urgent": 0, "high": 1, "normal": 2}
    suggestions.sort(key=lambda s: priority_order.get(s["priority"], 3))

    return suggestions[:5]  # Max 5 suggestions at a time
