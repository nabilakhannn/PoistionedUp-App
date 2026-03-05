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
    """Return the most recent trend analyzer research report for THIS brand.

    Fetches the latest deliverable from the trend-analyzer agent
    to avoid repeating recently researched topics.

    BUG FIX (Slice 90): Added brand_id filter — previously all brands shared
    the same trend memory which caused cross-brand contamination.
    """
    if not _is_valid_uuid(brand_id):
        return "[trend_memory unavailable — invalid brand_id]"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        user_id = _get_user_for_brand(brand_id, sb)

        # trend-analyzer uses created_by_agent_id = "trend-analyzer"
        # Filter by user_id (brand owner) to isolate per-brand memory
        result = (
            sb.table("agent_deliverables")
            .select("content, created_at")
            .eq("created_by_agent_id", "trend-analyzer")
            .eq("user_id", user_id)
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


def get_brand_context(brand_id: str) -> Optional[dict]:
    """Fetch deep brand intelligence dossier as a dict for prompt injection.

    Returns the full profile including anxiety_list, power_words, metaphors,
    emotional journals, etc. Returns None on failure (prompt will still work).
    """
    if not _is_valid_uuid(brand_id):
        return None
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        result = (
            sb.table("personal_brands")
            .select("name, description, profile_json")
            .eq("id", brand_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        profile = row.get("profile_json") or {}
        ctx = {
            "name": row.get("name", ""),
            "voice": profile.get("voice", ""),
            "ica": profile.get("ica", ""),
            "positioning": profile.get("positioning", ""),
            "offer": profile.get("offer", ""),
            "tagline": profile.get("tagline", ""),
            "transformation_zero": profile.get("transformation_zero", ""),
            "transformation_dream": profile.get("transformation_dream", ""),
            "anxiety_list": profile.get("anxiety_list", [])[:10],
            "benefit_list": profile.get("benefit_list", [])[:10],
            "power_words": profile.get("power_words", []),
            "industry_lingo": profile.get("industry_lingo", []),
            "metaphors": profile.get("metaphors", []),
            "content_pillars": profile.get("content_pillars", []),
        }
        # Pull latest 3 journal entries for grounding
        try:
            j = (
                sb.table("experience_journal")
                .select("summary, type")
                .eq("brand_id", brand_id)
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            ctx["emotional_journal_summary"] = [
                f"[{r.get('type','note')}] {str(r.get('summary',''))[:200]}"
                for r in (j.data or [])
            ]
        except Exception:
            ctx["emotional_journal_summary"] = []
        return ctx
    except Exception as exc:
        logger.warning("get_brand_context failed brand=%s: %s", brand_id, exc)
        return None


def get_hooks_for_brand(brand_id: str) -> str:
    """Fetch user's hook library and format for prompt injection.

    Returns a formatted string for inclusion in the writing prompt.
    Returns empty string if no hooks or on error (graceful degradation).
    """
    if not _is_valid_uuid(brand_id):
        return ""
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        # Look up user_id for this brand
        brand_row = sb.table("personal_brands").select("user_id").eq("id", brand_id).limit(1).execute()
        if not brand_row.data:
            return ""
        user_id = brand_row.data[0]["user_id"]

        result = (
            sb.table("hook_library")
            .select("hook_text, hook_type, times_used")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .order("times_used", desc=True)
            .limit(20)
            .execute()
        )
        if not result.data:
            return ""

        # Group by type
        grouped: dict = {}
        for h in result.data:
            t = h.get("hook_type", "custom")
            grouped.setdefault(t, [])
            grouped[t].append(h["hook_text"])

        lines = ["## Your Hook Library — Use These As Opening Line Examples\n"]
        for htype, texts in grouped.items():
            lines.append(f"\n### {htype.title()} Hooks")
            for text in texts[:4]:
                lines.append(f"- {text}")
        return "\n".join(lines) + "\n"

    except Exception as exc:
        logger.warning("get_hooks_for_brand failed brand=%s: %s", brand_id, exc)
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


def get_marketing_insights(brand_id: str) -> str:
    """Return the latest research brief for Sales agents.

    Sales newsletter and outreach agents read what Marketing researched
    so they can write content based on current trends without repeating
    the research phase.
    """
    if not _is_valid_uuid(brand_id):
        return "[marketing_insights unavailable — invalid brand_id]"

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        result = (
            sb.table("research_briefs")
            .select("content, run_at")
            .eq("brand_id", brand_id)
            .order("run_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return (
                "## Marketing Insights\n"
                "No recent research brief available. Write based on brand voice and ICA.\n"
            )

        content = str(result.data[0].get("content", ""))[:2000]
        date = str(result.data[0].get("run_at", ""))[:10]
        return f"## Latest Marketing Research ({date})\n{content}\n"

    except Exception as exc:
        logger.warning("get_marketing_insights failed brand=%s: %s", brand_id, exc)
        return "[marketing_insights temporarily unavailable]"


def get_knowledge_docs(user_id: str, brand_id: str, agent_id: Optional[str] = None) -> str:
    """Return knowledge documents (SOPs + user docs) for an agent.

    Two-tier: system SOPs (all users) + user docs (per brand).
    Filtered by agent_scope if agent_id provided.
    """
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(brand_id):
        return ""

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        # System docs
        system_docs = (
            sb.table("knowledge_documents")
            .select("title, content, doc_type, platform, scope, agent_scope")
            .eq("scope", "system")
            .execute()
            .data or []
        )

        # User docs for this brand
        user_docs = (
            sb.table("knowledge_documents")
            .select("title, content, doc_type, platform, scope, agent_scope")
            .eq("scope", "user")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .execute()
            .data or []
        )

        all_docs = system_docs + user_docs

        # Filter by agent scope
        if agent_id:
            filtered = []
            for doc in all_docs:
                agent_scope = doc.get("agent_scope") or []
                if not agent_scope or agent_id in agent_scope:
                    filtered.append(doc)
            all_docs = filtered

        if not all_docs:
            return ""

        lines = ["## Knowledge Base — Writing Guidelines\n"]
        for doc in all_docs:
            scope_label = "[SYSTEM]" if doc.get("scope") == "system" else "[YOUR DOC]"
            platform_label = doc.get("platform", "all").upper()
            lines.append(f"### {scope_label} [{platform_label}] {doc['title']}")
            lines.append(str(doc.get("content", ""))[:500])
            lines.append("")

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("get_knowledge_docs failed user=%s brand=%s: %s", user_id, brand_id, exc)
        return ""


def get_relevant_experiences(
    user_id: str,
    brand_id: str,
    topic: str = "",
    max_entries: int = 5,
) -> tuple:
    """Return relevant journal entries for grounding content in real experience.

    Selection strategy (in order of priority):
      1. Pinned entries — user explicitly flagged these (always included, up to max_entries)
      2. Never-used entries — prefer fresh material the agent hasn't touched yet
      3. Least-recently-used — avoids repeating the same stories

    When a topic is provided (e.g. Phase 1 research brief), Claude Haiku ranks
    all candidates by relevance and the top max_entries are chosen.

    Returns:
      tuple[str, list[str]]: (formatted_context_for_prompt, list_of_selected_entry_ids)
      The caller should pass the IDs to mark_experiences_used() after a successful write.
    """
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(brand_id):
        return ("", [])

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        # Fetch all entries — ordered: pinned first, then least-used, then oldest
        result = (
            sb.table("experience_journal")
            .select("id, title, source_type, raw_content, tags, created_at, times_used, pinned")
            .eq("user_id", user_id)
            .eq("brand_id", brand_id)
            .order("pinned", desc=True)
            .order("times_used", desc=False)
            .order("created_at", desc=False)
            .limit(50)
            .execute()
        )

        if not result.data:
            return ("", [])

        all_entries = result.data

        # If topic is provided, use AI to rank by relevance
        selected = _rank_entries_by_topic(all_entries, topic, max_entries) if topic.strip() else all_entries[:max_entries]

        selected_ids = [e["id"] for e in selected]

        lines = ["## Your Real Experiences — Use These in Your Writing\n"]
        lines.append(
            "Ground your content in these real experiences. "
            "Reference them naturally (e.g., 'I was on a call last week...', "
            "'A client told me...', 'I just helped someone with...'):\n"
        )

        for entry in selected:
            title = entry.get("title") or entry.get("source_type", "Experience")
            preview = str(entry.get("raw_content", ""))[:400].strip()
            tags = entry.get("tags") or []
            date = str(entry.get("created_at", ""))[:10]
            used = entry.get("times_used", 0)
            pinned = entry.get("pinned", False)

            pin_marker = " 📌" if pinned else ""
            used_note = " (never used before — fresh story)" if used == 0 else f" (used {used}x)"
            lines.append(f"**{title}**{pin_marker} — {date}{used_note}")
            if tags:
                lines.append(f"Tags: {', '.join(tags)}")
            lines.append(preview + ("..." if len(str(entry.get("raw_content", ""))) > 400 else ""))
            lines.append("")

        return ("\n".join(lines), selected_ids)

    except Exception as exc:
        logger.warning("get_relevant_experiences failed user=%s brand=%s: %s", user_id, brand_id, exc)
        return ("", [])


def _rank_entries_by_topic(entries: list, topic: str, max_entries: int) -> list:
    """Use Claude Haiku to rank journal entries by relevance to a topic.

    Falls back to the default ordering (pinned first, least-used) if the
    AI call fails. Pinned entries are always preserved in the final selection.

    Returns the top max_entries entries from AI ranking.
    """
    pinned = [e for e in entries if e.get("pinned")]
    unpinned = [e for e in entries if not e.get("pinned")]

    # If we already have enough pinned entries, skip AI ranking
    if len(pinned) >= max_entries:
        return pinned[:max_entries]

    slots_left = max_entries - len(pinned)

    # Build compact entry summaries for Haiku (avoid sending huge content)
    summaries = []
    for e in unpinned[:30]:  # cap at 30 to stay within Haiku token budget
        preview = str(e.get("raw_content", ""))[:150].strip().replace("\n", " ")
        summaries.append(f"ID:{e['id']} | {e.get('title') or e.get('source_type','note')} | {preview}")

    if not summaries:
        return pinned

    try:
        import openai as _openai
        client = _openai.OpenAI()

        prompt = (
            f"You are selecting journal entries to ground a LinkedIn post.\n\n"
            f"Topic/Research Brief (first 400 chars):\n{topic[:400]}\n\n"
            f"Journal entries (one per line — ID | title | preview):\n"
            + "\n".join(summaries)
            + f"\n\nReturn ONLY the {slots_left} most relevant entry IDs, "
            f"comma-separated. Prefer entries that haven't been used recently. "
            f"Example: abc-123, def-456"
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()

        # Parse IDs from response
        id_set = {e["id"] for e in unpinned}
        selected_ids = [
            part.strip()
            for part in raw.replace("\n", ",").split(",")
            if part.strip() in id_set
        ][:slots_left]

        selected_unpinned = [e for e in unpinned if e["id"] in selected_ids]

        # Fill remaining slots with least-used if AI returned fewer than needed
        if len(selected_unpinned) < slots_left:
            seen = {e["id"] for e in selected_unpinned}
            for e in unpinned:
                if e["id"] not in seen and len(selected_unpinned) < slots_left:
                    selected_unpinned.append(e)

        return pinned + selected_unpinned

    except Exception as exc:
        logger.warning("_rank_entries_by_topic AI call failed: %s — using default order", exc)
        return pinned + unpinned[:slots_left]


def mark_experiences_used(entry_ids: list) -> None:
    """Atomically increment times_used + set last_used_at for each entry.

    Called by the pipeline after a successful Phase 2 write so the same
    journal entries are not repeated indefinitely. Silent failure — never
    blocks the pipeline.
    """
    if not entry_ids:
        return

    # Validate every ID before sending to DB
    valid_ids = [eid for eid in entry_ids if _is_valid_uuid(str(eid))]
    if not valid_ids:
        return

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        sb.rpc("increment_journal_usage", {"entry_ids": valid_ids}).execute()
        logger.info("Marked %d journal entries as used: %s", len(valid_ids), valid_ids)
    except Exception as exc:
        logger.warning("mark_experiences_used failed: %s", exc)


def save_research_brief(user_id: str, brand_id: str, content: str) -> bool:
    """Save Phase 1 research output to research_briefs table.

    This makes Marketing research available to Sales agents (newsletter, outreach)
    without requiring them to re-run the expensive research phase.
    Silent failure — never blocks the pipeline.
    """
    if not _is_valid_uuid(user_id) or not _is_valid_uuid(brand_id):
        return False

    try:
        from app.deps import get_admin_client
        sb = get_admin_client()

        sb.table("research_briefs").insert({
            "user_id": user_id,
            "brand_id": brand_id,
            "content": content[:50_000],
            "topic_count": content.count("### Topic") or 3,
        }).execute()

        logger.info("research_brief saved user=%s brand=%s", user_id, brand_id)
        return True

    except Exception as exc:
        logger.warning("save_research_brief failed user=%s brand=%s: %s", user_id, brand_id, exc)
        return False


def check_monthly_budget(user_id: str) -> Optional[str]:
    """Check if user has exceeded their monthly AI budget.

    Returns an error message string if over budget, None if within budget.
    Checks pipeline_settings.monthly_budget_usd vs actual monthly spend
    from sdk_agent_runs + tool_use agent costs.
    """
    if not _is_valid_uuid(user_id):
        return None

    try:
        from app.deps import get_admin_client
        from datetime import datetime, timezone
        sb = get_admin_client()

        # Get budget setting
        settings_row = (
            sb.table("pipeline_settings")
            .select("monthly_budget_usd, budget_alert_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not settings_row.data:
            return None  # No settings = no cap

        monthly_budget = float(settings_row.data[0].get("monthly_budget_usd") or 20.0)
        if monthly_budget <= 0:
            return None  # Zero or negative = no cap

        # Get this month's spend from sdk_agent_runs (using total_cost field if available)
        # Fall back to token count * estimated cost
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        runs_result = (
            sb.table("sdk_agent_runs")
            .select("total_tokens, created_at")
            .eq("user_id", user_id)
            .gte("created_at", month_start.isoformat())
            .execute()
        )

        total_tokens = sum(
            row.get("total_tokens") or 0
            for row in (runs_result.data or [])
        )

        # Estimate cost: ~$0.003 per 1K tokens (average across models)
        estimated_cost = (total_tokens / 1000) * 0.003

        if estimated_cost >= monthly_budget:
            return (
                f"Monthly AI budget of ${monthly_budget:.2f} reached "
                f"(estimated spend: ${estimated_cost:.2f}). "
                "Update your budget in Settings → Pipeline to continue."
            )

        return None

    except Exception as exc:
        logger.warning("check_monthly_budget failed user=%s: %s", user_id, exc)
        return None  # Silent fail — don't block pipeline on budget check errors


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
    experiences_ctx: str = "",
    brand_context: Optional[dict] = None,
    hooks_ctx: str = "",
    topic_focus: Optional[str] = None,
) -> str:
    """Return the system prompt for the writing phase.

    brand_context (from fetch_brand_profile) is pre-injected so the copywriter
    has deep brand intelligence WITHOUT needing an extra tool-call round-trip.
    """
    rejection_section = (
        f"\n{rejection_history}\n" if rejection_history.strip() else ""
    )
    experiences_section = (
        f"\n{experiences_ctx}\n" if experiences_ctx.strip() else ""
    )
    hooks_section = f"\n{hooks_ctx}\n" if hooks_ctx.strip() else ""

    # ── Pre-inject deep brand intelligence ───────────────────────────────
    brand_section = ""
    if brand_context:
        bc = brand_context
        anxiety = bc.get("anxiety_list", [])
        benefits = bc.get("benefit_list", [])
        power_words = bc.get("power_words", [])
        lingo = bc.get("industry_lingo", [])
        metaphors = bc.get("metaphors", [])
        journals = bc.get("emotional_journal_summary", [])
        brand_section = (
            "\n## Brand Intelligence (Use This — Do NOT Be Generic)\n"
            f"**Voice:** {bc.get('voice', '')}\n"
            f"**ICA:** {bc.get('ica', '')}\n"
            f"**Positioning:** {bc.get('positioning', '')}\n"
            f"**Tagline:** {bc.get('tagline', '')}\n"
            f"**Transformation:** {bc.get('transformation_zero', '')} → {bc.get('transformation_dream', '')}\n"
            f"**ICA's TOP FEARS (mirror these):** {', '.join(str(x) for x in anxiety[:5]) if anxiety else 'not set'}\n"
            f"**ICA's TOP DESIRES (speak to these):** {', '.join(str(x) for x in benefits[:5]) if benefits else 'not set'}\n"
            f"**Power Words (use their vocabulary):** {', '.join(str(x) for x in power_words[:10]) if power_words else 'not set'}\n"
            f"**Industry Lingo:** {', '.join(str(x) for x in lingo[:8]) if lingo else 'not set'}\n"
            f"**Resonant Metaphors:** {', '.join(str(x) for x in metaphors[:3]) if metaphors else 'not set'}\n"
        )
        if journals:
            brand_section += (
                "**Real Stories to Ground Your Post (use at least one):**\n"
                + "\n".join(f"  - {j}" for j in journals) + "\n"
            )

    topic_section = ""
    if topic_focus and topic_focus.strip():
        topic_section = (
            "## PRIORITY TOPIC (User-Approved)\n"
            f"Write specifically about: **{topic_focus.strip()}**\n"
            "Use the brand context below but centre this post on the topic above.\n\n"
        )

    research_section = ""
    if research_brief and research_brief.strip():
        research_section = f"## Research Brief\n{research_brief}"

    return (
        "You are an expert LinkedIn Copywriter for personal brand creators.\n\n"
        "Your job: Write ONE compelling LinkedIn post based on the research brief below.\n\n"
        f"{topic_section}"
        f"{analytics_ctx}\n"
        f"{brand_section}"
        f"{hooks_section}"
        f"{rejection_section}"
        f"{experiences_section}"
        "## Writing Rules\n"
        "- Open with a strong hook: question, bold claim, or provocative statement\n"
        "- Short sentences, line breaks between every 2-3 lines\n"
        "- No em dashes (— or –), no 'in conclusion', no AI-tell phrases\n"
        "- First-person voice (I, my, we)\n"
        "- End with a clear, specific call to action\n"
        "- Target: 150–300 words\n"
        "- CRITICAL: Sound like a real human, not an AI. Use specific numbers, names, real experiences.\n"
        "- Mirror the ICA's fears and desires. Use their exact vocabulary (power words above).\n\n"
        "## Your Process\n"
        "1. Call read_playbook(agent_id='copywriter', user_id=<user_id>) to load your playbook\n"
        "2. Call fetch_brand_profile(brand_id=<brand_id>) to load full brand voice + intelligence\n"
        "3. Write the post — ground it in a real story, specific number, or fear from the Brand Intelligence above\n"
        "4. Call score_content_quality(content=<your draft>) to self-check\n"
        "5. If issues found, revise once — then output the final post\n"
        "6. Output ONLY the final post text (no commentary)\n\n"
        f"{research_section}"
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
    source: str = "autonomous",
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
            "source": source,
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
