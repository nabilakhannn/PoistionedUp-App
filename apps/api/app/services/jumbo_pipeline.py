"""Jumbo Pipeline Service — Slice 89.

Provides context helpers, prompt builders, and save/notify utilities
for the multi-phase automated content pipeline:

  Phase 1: Research  — web search + competitor + analytics context injection
  Phase 2: Write     — brand-voice copy using research brief + analytics history
  Phase 3: QA        — score gate (80+), save deliverable, notify user

All functions are stateless and single-responsibility (SOLID).
Heavy lifting (LLM calls) stays in tool_use_agents.py — this module
only handles data retrieval, prompt assembly, and result persistence.
"""

from __future__ import annotations

import logging
import re
import uuid as _uuid
from typing import Optional

logger = logging.getLogger("app.services.jumbo_pipeline")

# Strict UUID pattern — prevents injection via brand_id / user_id params
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))


# ── Context getters ────────────────────────────────────────────────────────


def get_analytics_context(brand_id: str) -> str:
    """Return top-performing post examples for this brand.

    Queries agent_deliverables for the 5 highest-QA-score published posts.
    Returns formatted markdown suitable for LLM prompt injection.
    """
    if not _is_valid_uuid(brand_id):
        return "[analytics_context unavailable — invalid brand_id]"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        result = (
            sb.table("agent_deliverables")
            .select("content, qa_score, deliverable_type, created_at")
            .eq("user_id", _get_user_for_brand(brand_id, sb))
            .eq("status", "published")
            .order("qa_score", desc=True)
            .limit(5)
            .execute()
        )

        if not result.data:
            return (
                "## Analytics Context\n"
                "No published posts yet — write content that closely matches the brand voice.\n"
            )

        lines = ["## Analytics Context — Top Performing Posts\n"]
        lines.append("Study these examples for format, hook style, and tone:\n")
        for i, row in enumerate(result.data, 1):
            preview = str(row.get("content", ""))[:180].strip()
            score = row.get("qa_score") or 0
            lines.append(f"**Post {i}** (QA: {score}/100)\n```\n{preview}...\n```\n")

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("get_analytics_context failed brand=%s: %s", brand_id, exc)
        return "[analytics_context temporarily unavailable]"


def get_competitor_context(brand_id: str) -> str:
    """Return tracked competitor names, threat levels, and niches.

    Queries the competitors table for active competitors linked to this brand.
    Returns formatted markdown for LLM prompt injection.
    """
    if not _is_valid_uuid(brand_id):
        return "[competitor_context unavailable — invalid brand_id]"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        result = (
            sb.table("competitors")
            .select("name, threat_level, niche, positioning")
            .eq("brand_id", brand_id)
            .eq("status", "active")
            .order("threat_level", desc=True)
            .limit(5)
            .execute()
        )

        if not result.data:
            return (
                "## Competitor Context\n"
                "No competitors tracked yet — create original angle content.\n"
            )

        lines = ["## Competitor Context — Tracked Competitors\n"]
        lines.append("Create content that these competitors are NOT covering:\n")
        for comp in result.data:
            name = comp.get("name", "Unknown")
            threat = comp.get("threat_level", 3)
            niche = comp.get("niche") or comp.get("positioning") or "general"
            lines.append(f"- **{name}** (threat: {threat}/5) — niche: {niche}")

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("get_competitor_context failed brand=%s: %s", brand_id, exc)
        return "[competitor_context temporarily unavailable]"


def get_trend_memory(brand_id: str) -> str:
    """Return the most recent trend analyzer research report.

    Fetches the latest deliverable from the trend-analyzer agent
    to avoid repeating recently researched topics.
    """
    if not _is_valid_uuid(brand_id):
        return "[trend_memory unavailable — invalid brand_id]"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        # trend-analyzer uses created_by_agent_id = "trend-analyzer"
        result = (
            sb.table("agent_deliverables")
            .select("content, created_at")
            .eq("created_by_agent_id", "trend-analyzer")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return "## Previous Research\nNo previous trend research — this is the first run.\n"

        content = str(result.data[0].get("content", ""))[:2000]
        date = str(result.data[0].get("created_at", ""))[:10]
        return f"## Previous Research ({date})\nDo NOT repeat these topics:\n\n{content}\n"

    except Exception as exc:
        logger.warning("get_trend_memory failed brand=%s: %s", brand_id, exc)
        return "[trend_memory temporarily unavailable]"


def get_rejection_history(user_id: str, brand_id: str) -> str:
    """Return recent rejection tags from agent_memory (voice_feedback type).

    The Home Inbox reject flow saves rejection tags to agent_memory.
    This function surfaces them so the Copywriter avoids repeating mistakes.
    """
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(brand_id):
        return ""

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        result = (
            sb.table("agent_memory")
            .select("content, created_at")
            .eq("user_id", user_id)
            .ilike("content", "%voice_feedback%")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if not result.data:
            return ""

        lines = ["## User Rejection History — AVOID These Patterns\n"]
        for row in result.data:
            lines.append(f"- {str(row.get('content', ''))[:150]}")
        return "\n".join(lines) + "\n"

    except Exception as exc:
        logger.warning("get_rejection_history failed user=%s: %s", user_id, exc)
        return ""


def _get_user_for_brand(brand_id: str, sb) -> str:
    """Helper: look up the user_id that owns this brand."""
    try:
        result = (
            sb.table("personal_brands")
            .select("user_id")
            .eq("id", brand_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["user_id"]
    except Exception:
        pass
    return ""


# ── Prompt builders ────────────────────────────────────────────────────────


def build_research_prompt(
    analytics_ctx: str,
    competitor_ctx: str,
    trend_memory: str,
) -> str:
    """Return the system prompt for the research phase."""
    return (
        "You are a professional Trend Analyst and Content Research Specialist.\n\n"
        "Your job: Research 3 high-potential content topics for a personal brand creator.\n\n"
        "Topics must be:\n"
        "1. Currently trending (verify with web_search)\n"
        "2. Distinct from competitors' recent content\n"
        "3. Aligned with formats that have performed well for this brand\n\n"
        f"{analytics_ctx}\n\n"
        f"{competitor_ctx}\n\n"
        f"{trend_memory}\n\n"
        "## Your Process\n"
        "1. Call read_playbook(agent_id='trend-analyzer', user_id=<user_id>) to load guidelines\n"
        "2. Use web_search to find 2-3 trending topics in the brand's niche (real, current data)\n"
        "3. For each topic: note why it's trending, a unique angle, and a strong hook idea\n"
        "4. Use synthesize_research to combine findings into a structured brief\n"
        "5. Recommend ONE topic to write first, with reasoning\n\n"
        "## Output Format\n"
        "---\n"
        "## Research Brief\n\n"
        "### Topic 1: [Title]\n"
        "- Trending because: ...\n"
        "- Unique angle: ...\n"
        "- Best hook: ...\n\n"
        "### Topic 2: [Title]\n"
        "...\n\n"
        "### Recommended: [Topic]\n"
        "Reason: ...\n"
        "---\n\n"
        "Be specific. Use real data and sources. No vague generalities."
    )


def build_writing_prompt(
    research_brief: str,
    analytics_ctx: str,
    rejection_history: str,
) -> str:
    """Return the system prompt for the writing phase."""
    rejection_section = (
        f"\n{rejection_history}\n" if rejection_history.strip() else ""
    )
    return (
        "You are an expert LinkedIn Copywriter for personal brand creators.\n\n"
        "Your job: Write ONE compelling LinkedIn post based on the research brief below.\n\n"
        f"{analytics_ctx}\n"
        f"{rejection_section}"
        "## Writing Rules\n"
        "- Open with a strong hook: question, bold claim, or provocative statement\n"
        "- Short sentences, line breaks between every 2-3 lines\n"
        "- No em dashes (— or –), no 'in conclusion', no AI-tell phrases\n"
        "- First-person voice (I, my, we)\n"
        "- End with a clear, specific call to action\n"
        "- Target: 150–300 words\n\n"
        "## Your Process\n"
        "1. Call read_playbook(agent_id='copywriter', user_id=<user_id>) to load your playbook\n"
        "2. Call fetch_brand_profile(brand_id=<brand_id>) to load voice, ICA, and positioning\n"
        "3. Write the post using the research brief and brand voice\n"
        "4. Call score_content_quality(content=<your draft>) to self-check\n"
        "5. If issues found, revise once — then output the final post\n"
        "6. Output ONLY the final post text (no commentary)\n\n"
        "## Research Brief\n"
        f"{research_brief[:3000]}"
    )


def build_qa_prompt() -> str:
    """Return the system prompt for the QA review phase."""
    return (
        "You are a Content Quality Reviewer for a personal brand content agency.\n\n"
        "Your job: Score a LinkedIn post and output a structured review.\n\n"
        "## Scoring Rubric (100 points)\n"
        "- Voice authenticity (25 pts): Human-sounding? No AI tells?\n"
        "- Hook strength (25 pts): First line stops the scroll?\n"
        "- Structure (20 pts): Short lines, easy flow, readable?\n"
        "- Value delivery (20 pts): Teaches, inspires, or entertains clearly?\n"
        "- CTA clarity (10 pts): Specific, natural call to action?\n\n"
        "## Your Process\n"
        "1. Call score_content_quality(content=<post>) for a mechanical check\n"
        "2. Apply the rubric above\n"
        "3. Identify 1-3 specific improvements\n\n"
        "## Required Output Format (use EXACTLY this)\n"
        "SCORE: [number]/100\n"
        "VERDICT: [PASS or FAIL]\n"
        "STRENGTHS:\n"
        "- [strength 1]\n"
        "- [strength 2]\n"
        "IMPROVEMENTS:\n"
        "- [improvement 1]\n"
        "- [improvement 2]\n"
    )


# ── Score parser ───────────────────────────────────────────────────────────


def parse_qa_score(qa_response: str) -> int:
    """Extract numeric QA score from the QA agent's response.

    Looks for 'SCORE: 85/100' or 'Score: 85' patterns.
    Returns 0 if no valid score found.
    """
    # Primary pattern: SCORE: 85/100
    match = re.search(r"SCORE:\s*(\d{1,3})\s*(?:/\s*100)?", qa_response, re.IGNORECASE)
    if match:
        return min(100, max(0, int(match.group(1))))

    # Fallback: any XX/100 pattern
    match = re.search(r"(\d{2,3})\s*/\s*100", qa_response)
    if match:
        return min(100, max(0, int(match.group(1))))

    return 0


# ── Persistence helpers ────────────────────────────────────────────────────


def save_deliverable(
    user_id: str,
    content: str,
    qa_score: int,
    title: Optional[str] = None,
) -> str:
    """Save draft to agent_deliverables. Returns deliverable_id (empty string on error).

    status=review   if qa_score >= 80  → appears in Home Inbox for approval
    status=failed_qa if qa_score < 80  → logged but not surfaced to user
    """
    status = "review" if qa_score >= 80 else "failed_qa"
    deliverable_id = str(_uuid.uuid4())
    post_title = title or f"Pipeline post — QA {qa_score}/100"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        sb.table("agent_deliverables").insert({
            "id": deliverable_id,
            "user_id": user_id,
            "title": post_title[:200],
            "content": content[:100_000],
            "deliverable_type": "content",
            "created_by_agent_id": "copywriter",
            "status": status,
            "qa_score": qa_score,
        }).execute()

        logger.info(
            "Saved deliverable id=%s user=%s qa=%d status=%s",
            deliverable_id, user_id, qa_score, status,
        )
        return deliverable_id

    except Exception as exc:
        logger.error("save_deliverable failed user=%s: %s", user_id, exc)
        return ""


def notify_approval_needed(
    user_id: str,
    deliverable_id: str,
    content_preview: str = "",
) -> None:
    """Create an agent_notification prompting the user to approve the new post.

    Uses the existing agent_notifications table (Slice 73).
    Silent failure — never blocks the pipeline.
    """
    if not _is_valid_uuid(user_id):
        return

    preview = content_preview[:80].strip()
    body = (
        f'New post ready for your approval: "{preview}…"'
        if preview
        else "New post ready for your approval."
    )

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        sb.table("agent_notifications").insert({
            "user_id": user_id,
            "title": "Post ready for approval",
            "body": body,
            "notification_type": "content_ready",
            "priority": "high",
            "from_agent_id": "jumbo",
            "metadata": {"deliverable_id": deliverable_id},
        }).execute()

    except Exception as exc:
        logger.warning("notify_approval_needed failed user=%s: %s", user_id, exc)
