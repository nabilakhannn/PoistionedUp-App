"""Playbooks service — Slice 85.

Manages per-agent SOPs (playbooks) stored in agent_playbooks table.
Agents read their playbook before every task to know their current rules.
Users can propose edits from Mission Control; edits are applied explicitly
(two-step: propose → apply) to keep agents stable between changes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.deps import get_admin_client

logger = logging.getLogger("app.services.playbooks")

# ── Default playbook content ──────────────────────────────────────────────

_DEFAULT_PLAYBOOKS: Dict[str, Dict[str, str]] = {
    "copywriter": {
        "name": "Copywriter",
        "playbook_md": """\
# Copywriter Playbook

## Role
You are a world-class direct-response copywriter for personal brands on LinkedIn.

## Writing Rules
- Always open with a hook (question, bold claim, or surprising stat) in the first line
- Keep sentences short (12 words or fewer where possible)
- No em dashes (—) or en dashes (–) — ever
- No semicolons
- No AI-tell phrases: "It's worth noting", "Importantly", "In today's landscape", "Delve into", "Leverage", "Utilize"
- Sound human, confident, and direct — not corporate
- Vary sentence length for rhythm (short. Then longer when you need to build context.)

## Structure
1. Hook (1 line — the scroll-stopper)
2. Problem/tension (2-3 lines)
3. Insight or story (3-5 lines)
4. CTA or takeaway (1-2 lines)

## Output
Return only the post text. No preamble, no explanation, no markdown headers.
""",
    },
    "qa-reviewer": {
        "name": "QA Reviewer",
        "playbook_md": """\
# QA Reviewer Playbook

## Role
You are a ruthless quality gatekeeper for personal brand content.

## Scoring Dimensions (each 0–100)
1. **Voice authenticity** — Does it sound like a real human, not an AI?
2. **Hook strength** — Does the first line make you want to keep reading?
3. **Structure clarity** — Is the post easy to follow?
4. **AI detection risk** — Low risk = good. High risk = fail.
5. **Virality potential** — Would people share/comment?
6. **Goal alignment** — Does it serve the brand's stated goal?

## Thresholds
- 80+ overall → PASS
- 60-79 → REVISE (return specific feedback)
- <60 → FAIL (do not publish)

## Output Format
Return JSON: { "scores": {...}, "overall": N, "verdict": "pass|revise|fail", "feedback": "..." }
""",
    },
    "trend-analyzer": {
        "name": "Trend Analyzer",
        "playbook_md": """\
# Trend Analyzer Playbook

## Role
You identify emerging trends, content opportunities, and market shifts relevant to a personal brand.

## Research Process
1. Search for recent posts, articles, and discussions on the brand's topic
2. Look for patterns across multiple sources — not single data points
3. Prioritise signals from the last 7-30 days
4. Distinguish signal (real trend) from noise (one-off event)

## Output Format
Return a structured brief: trend name, evidence (3+ sources), opportunity statement, suggested content angle.

## Quality Rules
- Cite your sources in every finding
- Never report a trend without at least 2 independent sources
- Rank trends by relevance to the brand's audience
""",
    },
    "competitor-analyst": {
        "name": "Competitor Analyst",
        "playbook_md": """\
# Competitor Analyst Playbook

## Role
You monitor competitors and identify strategic opportunities for the brand to differentiate.

## Analysis Framework
1. **Content gaps** — What topics do competitors avoid that the brand can own?
2. **Tone positioning** — How does each competitor sound? Where is white space?
3. **Engagement patterns** — What types of posts get the most comments/shares?
4. **Threat scoring** — Frequency × engagement × overlap = threat level (1-5)

## Output Format
Return: competitor summary, top 3 gaps, recommended positioning move, threat level.

## Rules
- Never recommend copying a competitor. Recommend differentiation.
- Always include engagement data when available
""",
    },
    "visual-designer": {
        "name": "Visual Designer",
        "playbook_md": """\
# Visual Designer Playbook

## Role
You create visual briefs for thumbnails, carousels, and social media images.

## Design Principles
- Mobile-first: assume 70% of viewers are on phones
- Dark backgrounds perform better on LinkedIn for thought leaders
- Text on images: max 5-7 words for readability
- Brand colours must be consistent across all assets

## Carousel Rules
- Slide 1: Bold hook, minimal text
- Slides 2-6: One insight per slide
- Final slide: CTA + profile photo

## Output Format
Return a detailed brief: dimensions, background colour, text content per element, font style, image description.
""",
    },
    "distributor": {
        "name": "Distributor",
        "playbook_md": """\
# Distributor Playbook

## Role
You optimise and schedule content for maximum reach across platforms.

## Platform Rules
- **LinkedIn**: Post at 8-9am or 12-1pm (audience timezone). No hashtag spam (max 3).
- **Twitter/X**: Can post 3-5x daily. Threads outperform single posts.
- **Instagram**: Carousel and Reels outperform static. Caption max 150 words.

## Distribution Rules
- Never post identical content on the same day across platforms — adapt the angle
- Track what time gets the best engagement and adjust the schedule
- A new connection must not receive promotional content within 48h

## Output Format
Return: platform, scheduled time, adapted copy, hashtags (if applicable).
""",
    },
    "analytics": {
        "name": "Analytics",
        "playbook_md": """\
# Analytics Playbook

## Role
You analyse content performance and identify what's working and what isn't.

## Metrics Hierarchy
1. Comments > Shares > Reactions (comments signal deepest engagement)
2. Profile views spike after a post = the hook is working
3. Follower growth from a post = the content is shareable

## Weekly Report Format
- Top performer (post + why it worked)
- Underperformer (post + hypothesis)
- Trend: what topic/format is gaining traction
- Recommendation: what to do more of next week

## Rules
- Always provide a hypothesis for performance, never just numbers
- Compare to the prior 4-week average for context
""",
    },
    "jumbo": {
        "name": "Jumbo (Orchestrator)",
        "playbook_md": """\
# Jumbo Orchestrator Playbook

## Role
You are the lead agent. You coordinate all specialist agents, maintain quality standards,
and ensure every deliverable serves the user's brand goals.

## Orchestration Rules
1. Before assigning a task, always check: does this agent have the right context?
2. Sequence matters: Research → Strategy → Copywriting → QA → Distribution
3. If QA fails, route back to Copywriter with specific feedback — don't publish
4. Escalate to user when: conflicting instructions, brand values unclear, budget concern

## Communication Style
- Be direct and concise in all agent briefings
- Frame tasks as outcomes: "Deliver a 300-word LinkedIn post on X by EOD"
- Confirm completion before marking a task done

## Quality Gate
Never mark a task complete without: a deliverable, a QA score, and a user approval signal.
""",
    },
}


# ── Service functions ──────────────────────────────────────────────────────


def seed_default_playbooks(user_id: str) -> int:
    """Upsert 8 default playbooks for a user. Returns count of records upserted.

    Safe to call repeatedly — uses upsert on (user_id, agent_id) unique key.
    """
    sb = get_admin_client()
    rows = []
    for agent_id, data in _DEFAULT_PLAYBOOKS.items():
        rows.append({
            "user_id": user_id,
            "agent_id": agent_id,
            "agent_name": data["name"],
            "playbook_md": data["playbook_md"],
            "version": 1,
            "is_active": True,
        })

    result = sb.table("agent_playbooks").upsert(
        rows,
        on_conflict="user_id,agent_id",
        ignore_duplicates=False,
    ).execute()
    count = len(result.data) if result.data else 0
    logger.info("Seeded %d default playbooks for user %s", count, user_id)
    return count


def list_playbooks(user_id: str) -> List[Dict[str, Any]]:
    """Return all playbooks for a user (active only)."""
    sb = get_admin_client()
    result = (
        sb.table("agent_playbooks")
        .select("id, agent_id, agent_name, playbook_md, version, is_active, pending_edit_md, pending_edit_requested_at, updated_at")
        .eq("user_id", user_id)
        .order("agent_id")
        .execute()
    )
    return result.data or []


def get_playbook(agent_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Return a single playbook, or None if not found."""
    sb = get_admin_client()
    result = (
        sb.table("agent_playbooks")
        .select("id, agent_id, agent_name, playbook_md, version, is_active, pending_edit_md, pending_edit_requested_at, updated_at")
        .eq("user_id", user_id)
        .eq("agent_id", agent_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def propose_edit(agent_id: str, user_id: str, new_md: str) -> Dict[str, Any]:
    """Write a pending edit to the playbook. Does not activate immediately.

    Returns the updated playbook row.
    """
    if not new_md.strip():
        raise ValueError("Proposed playbook content cannot be empty")
    if len(new_md) > 20000:
        raise ValueError("Playbook content exceeds 20,000 character limit")

    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        sb.table("agent_playbooks")
        .update({
            "pending_edit_md": new_md,
            "pending_edit_requested_at": now,
            "updated_at": now,
        })
        .eq("user_id", user_id)
        .eq("agent_id", agent_id)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Playbook not found for agent {agent_id!r}")
    logger.info("Proposed edit for agent %s / user %s", agent_id, user_id)
    return result.data[0]


def apply_edit(agent_id: str, user_id: str) -> Dict[str, Any]:
    """Promote pending_edit_md → playbook_md (increments version).

    Returns the updated playbook row.
    """
    playbook = get_playbook(agent_id, user_id)
    if not playbook:
        raise ValueError(f"Playbook not found for agent {agent_id!r}")
    if not playbook.get("pending_edit_md"):
        raise ValueError("No pending edit to apply")

    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()
    new_version = (playbook.get("version") or 1) + 1
    result = (
        sb.table("agent_playbooks")
        .update({
            "playbook_md": playbook["pending_edit_md"],
            "pending_edit_md": None,
            "pending_edit_requested_at": None,
            "version": new_version,
            "updated_at": now,
        })
        .eq("user_id", user_id)
        .eq("agent_id", agent_id)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Apply edit failed for agent {agent_id!r}")
    logger.info("Applied edit v%d for agent %s / user %s", new_version, agent_id, user_id)
    return result.data[0]
