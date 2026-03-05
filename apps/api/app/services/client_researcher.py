"""Client Researcher service — Slice 97.

Runs deep 5-layer research on a new client using the Brand Researcher agent:
  Layer 1 — LinkedIn & voice analysis
  Layer 2 — Pain point research (Agency Superpower method: 20-item anxiety list + journal)
  Layer 3 — Ideal outcome research (20-item benefit list + win journal)
  Layer 4 — Offer positioning (Hormozi Value Equation)
  Layer 5 — Competitive gap analysis (3-5 competitors)

Results are saved to personal_brands.profile_json.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.deps import get_admin_client
from app.utils.url_validation import validate_url_for_fetch
from app.services.tool_use_agents import run_tool_use_agent

logger = logging.getLogger("app.services.client_researcher")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ── System prompt for Brand Researcher agent ──────────────────────────────

_BRAND_RESEARCHER_SYSTEM = """\
You are a world-class brand researcher for content agencies.
Your job is to build a complete 8-Section Client Intelligence Dossier for a new client.
This is not surface-level research. Go deep on ALL 8 sections.

You have access to: web_search (Perplexity), synthesize_research (Gemini),
read_agent_training_docs, and fetch_brand_profile.

ALWAYS:
1. Start by calling read_agent_training_docs to load your methodology and training materials.
2. Run at minimum 6 web searches before synthesizing.
3. Return ONLY valid JSON in the exact schema below — no preamble, no explanation.

OUTPUT SCHEMA (return exactly this JSON):
{
  "content_pillars": ["3-5 topics they should build authority around"],
  "voice_adjectives": ["3 adjectives describing their writing voice"],
  "ica_summary": "One sentence: who their ideal client is",

  "transformation": {
    "zero_state": "BEFORE state — life in the pain. Specific moments: the 3am wake-up, the embarrassing conversation, what isn't working right now. Be vivid.",
    "dream_state": "AFTER state — life with the result. What does a Tuesday look like 6 months later? Be specific, not vague.",
    "journey": "The emotional arc from zero to dream — what shifts internally, not just externally."
  },

  "uvps": [
    "UVP 1: One sentence. Specific contrast vs. what competitors offer.",
    "UVP 2: Second angle — different proof or methodology.",
    "UVP 3: Third angle — speed, simplicity, or guarantee."
  ],
  "tagline": "One memorable positioning line under 10 words. Punchy. Memorable.",
  "niche_statement": "I help [SPECIFIC WHO] achieve [SPECIFIC WHAT] without [MAIN OBJECTION].",

  "metaphors": [
    "Analogy 1 — a story or comparison that makes their value click instantly",
    "Analogy 2 — simplifies their complex methodology",
    "Analogy 3 — makes the transformation feel inevitable"
  ],

  "hormozi": {
    "dream_outcome": "The ultimate transformation their client wants",
    "perceived_likelihood": "Why clients believe this person can deliver it",
    "time_to_result": "How fast clients typically see results",
    "effort_sacrifice": "How much effort the client has to put in",
    "guarantee": "A risk-reversal guarantee they could offer",
    "risk_reversals": ["2-3 specific de-risking elements"]
  },
  "anxiety_list": [
    "20 specific anxiety statements. Format: 'I [fear/worry/feel] ...'",
    "Must be SPECIFIC to this niche — not generic marketing language",
    "Reference real moments: the 3am wake-up, the embarrassing conversation",
    "... 20 total items"
  ],
  "benefit_list": [
    "20 specific benefit statements. Format: 'I finally ...' or 'Now I can ...'",
    "What their ideal client would say 6 months after getting the result",
    "... 20 total items"
  ],
  "emotional_pain_journal": "500-word journal from perspective of ideal client IN the pain. Use: exhausted, worried, stressed, fearful, confused, clueless, frustrated. Reference specific moments. Make it feel real.",
  "emotional_win_journal": "500-word journal from perspective of ideal client WHO HAS THE RESULT. Use: confident, proud, excited, accomplished, relieved, free. Make it feel real.",

  "your_story": {
    "background": "Their origin story — where they started, what problem they personally faced, what they had to figure out the hard way.",
    "growth_achievements": "Key milestones, client results (with numbers), credentials, proof that the methodology works.",
    "future_goals": "Where they're going — what they're building, what they want to be known for in 3 years.",
    "mission": "Why they do this beyond money — the deeper reason, the change they want to see."
  },

  "belief_framework": {
    "belief_statement": "The core belief their entire methodology is built on. One sentence. Contrarian or counterintuitive preferred.",
    "false_beliefs": [
      {
        "belief": "False belief 1 their ideal client holds that keeps them stuck",
        "counter_story": "A specific story, example, or reframe that breaks this belief and opens the door to their approach"
      },
      {
        "belief": "False belief 2",
        "counter_story": "Counter-story 2"
      },
      {
        "belief": "False belief 3",
        "counter_story": "Counter-story 3"
      }
    ]
  },

  "competitors": [
    {"name": "...", "positioning": "What they say", "gap": "What they don't say / their weakness"},
    "... 3-5 competitors"
  ],
  "competitor_gap": "The ONE single thing this client can own that nobody else is saying",
  "market_gap": "The broader underserved need in this niche — not about one competitor, but about the whole market.",

  "customer_segments": [
    {"segment": "Segment name (e.g. Solo Founder, Agency Owner)", "age": "e.g. 28-40", "problem": "Their specific burning problem"},
    {"segment": "Segment 2", "age": "...", "problem": "..."}
  ],
  "relevance_topics": ["Topics, creators, books, podcasts, or ideas their ICA already follows/reads"],

  "power_words": ["5-10 niche-specific vocabulary words their ICA uses in real conversation"],
  "industry_lingo": ["3-7 insider phrases or jargon that signal you belong to this world"],

  "first_week_angles": [
    {
      "hook": "The exact first line of the post",
      "angle_type": "anxiety|benefit|story|competitor|belief|metaphor",
      "driven_by": "Which anxiety_list or benefit_list or belief_framework item drives this",
      "offer_connection": "How this post connects to / leads to their offer"
    },
    "... 7 total angles (cover all angle types)"
  ],
  "research_completed_at": "ISO 8601 timestamp"
}
"""


async def research_client(
    brand_id: str,
    user_id: str,
    linkedin_url: str,
    website_url: Optional[str] = None,
    offer_description: Optional[str] = None,
    best_clients: Optional[str] = None,
    content_goal: Optional[str] = None,
) -> Dict[str, Any]:
    """Run 5-layer deep research on a client.

    Validates URLs (SSRF guard), runs the Brand Researcher SDK agent,
    parses the JSON dossier, and saves it to personal_brands.profile_json.

    Returns the full dossier dict.
    """
    # ── SSRF guard (OWASP A10) ─────────────────────────────────────────────
    validate_url_for_fetch(linkedin_url)
    if website_url:
        validate_url_for_fetch(website_url)

    # ── Fetch current brand profile for context ────────────────────────────
    sb = get_admin_client()
    brand_row = (
        sb.table("personal_brands")
        .select("name, description, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found for user {user_id!r}")

    brand_name = brand_row.data[0].get("name", "")
    existing_profile = brand_row.data[0].get("profile_json") or {}

    # ── Build user prompt ──────────────────────────────────────────────────
    user_prompt = f"""Research this client for a content agency onboarding:

CLIENT: {brand_name}
LINKEDIN: {linkedin_url}
WEBSITE: {website_url or "(not provided)"}
MAIN OFFER: {offer_description or "(not provided yet — infer from LinkedIn/website)"}
BEST 3 CLIENTS: {best_clients or "(not provided yet)"}
CONTENT GOAL: {content_goal or "Build authority and get new leads"}

INSTRUCTIONS:
1. Call read_agent_training_docs(agent_id="brand-researcher", user_id="{user_id}") to load your methodology
2. Search: "{brand_name} LinkedIn posts recent" — analyse voice and post topics
3. Search: "{brand_name} testimonials results case studies" — find social proof
4. Search for 3-5 competitors in their niche and their positioning gaps
5. Research the niche's ideal client pain points, anxieties, and false beliefs
6. Search: "{brand_name} origin story background" — find their personal story
7. Research the niche-specific vocabulary, insider lingo, and power words
8. Synthesize everything into the COMPLETE 8-section JSON dossier

Return ONLY valid JSON matching the exact schema in your system prompt. No other text."""

    # ── Run Brand Researcher agent ─────────────────────────────────────────
    result = run_tool_use_agent(
        agent_id="brand-researcher",
        task_type="client_research",
        system_prompt=_BRAND_RESEARCHER_SYSTEM,
        user_prompt=user_prompt,
        user_id=user_id,
        brand_id=brand_id,
        available_tools=["web_search", "synthesize_research", "read_agent_training_docs", "read_playbook"],
        temperature=0.6,
    )

    if not result.success:
        raise RuntimeError(f"Brand Researcher agent failed: {result.error}")

    # ── Parse JSON output ──────────────────────────────────────────────────
    dossier = _parse_dossier(result.content)

    # ── Merge with existing profile_json and save ──────────────────────────
    merged = {**existing_profile, **dossier}
    merged["research_source"] = {
        "linkedin_url": linkedin_url,
        "website_url": website_url or "",
    }

    sb.table("personal_brands").update({
        "profile_json": merged,
        "is_client_brand": True,
    }).eq("id", brand_id).eq("user_id", user_id).execute()

    logger.info("Client research saved for brand=%s", brand_id)
    return dossier


async def refresh_section(
    brand_id: str,
    user_id: str,
    section: str,
) -> Dict[str, Any]:
    """Regenerate a single section of the client dossier and merge it back.

    Supported sections: hormozi, competitors, anxiety_list, benefit_list,
    first_week_angles, emotional_pain_journal, emotional_win_journal.
    """
    allowed = {
        "hormozi", "competitors", "anxiety_list", "benefit_list",
        "first_week_angles", "emotional_pain_journal", "emotional_win_journal",
        "transformation", "uvps", "metaphors", "your_story",
        "belief_framework", "power_words", "market_gap",
    }
    if section not in allowed:
        raise ValueError(f"Unknown section {section!r}. Allowed: {sorted(allowed)}")

    sb = get_admin_client()
    brand_row = (
        sb.table("personal_brands")
        .select("name, description, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found for user {user_id!r}")

    profile = brand_row.data[0].get("profile_json") or {}
    brand_name = brand_row.data[0].get("name", "")

    user_prompt = f"""I need you to regenerate ONLY the '{section}' section for this client:

CLIENT: {brand_name}
EXISTING PROFILE SUMMARY:
- ICA: {profile.get("ica_summary", "not set")}
- Voice: {", ".join(profile.get("voice_adjectives", []) or [])}
- Content goal: {profile.get("content_goal", "build authority")}

Please:
1. Call read_agent_training_docs(agent_id="brand-researcher", user_id="{user_id}") first
2. Do fresh research as needed
3. Return ONLY a JSON object with the single key "{section}" and its new value

Example format: {{"{section}": [... or {{...}}]}}"""

    result = run_tool_use_agent(
        agent_id="brand-researcher",
        task_type=f"refresh_{section}",
        system_prompt=_BRAND_RESEARCHER_SYSTEM,
        user_prompt=user_prompt,
        user_id=user_id,
        brand_id=brand_id,
        available_tools=["web_search", "synthesize_research", "read_agent_training_docs"],
        temperature=0.7,
    )

    if not result.success:
        raise RuntimeError(f"Refresh failed: {result.error}")

    try:
        raw = result.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        patch = json.loads(raw)
    except Exception:
        raise RuntimeError(f"Agent returned non-JSON for section {section!r}: {result.content[:200]}")

    profile[section] = patch.get(section, patch)
    sb.table("personal_brands").update({"profile_json": profile}).eq("id", brand_id).eq("user_id", user_id).execute()

    return {section: profile[section]}


def get_report(brand_id: str, user_id: str) -> Dict[str, Any]:
    """Return the current client dossier from profile_json."""
    sb = get_admin_client()
    row = (
        sb.table("personal_brands")
        .select("name, description, profile_json, is_client_brand")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise ValueError(f"Brand {brand_id!r} not found")
    r = row.data[0]
    return {
        "brand_id": brand_id,
        "name": r.get("name", ""),
        "is_client_brand": r.get("is_client_brand", False),
        "profile": r.get("profile_json") or {},
    }


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_dossier(raw: str) -> Dict[str, Any]:
    """Extract JSON from agent output, stripping any markdown fences."""
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    # Try to extract JSON object if there's surrounding prose
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Brand Researcher returned non-JSON; using partial parse")
        # Return a minimal valid dossier so the UI doesn't break
        return {
            "content_pillars": [],
            "voice_adjectives": [],
            "ica_summary": "Research completed — review and edit manually",
            "hormozi": {},
            "anxiety_list": [],
            "benefit_list": [],
            "emotional_pain_journal": raw[:2000],
            "emotional_win_journal": "",
            "competitors": [],
            "competitor_gap": "",
            "first_week_angles": [],
        }
