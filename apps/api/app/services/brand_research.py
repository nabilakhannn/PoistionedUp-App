"""Brand Research Service: Automated 7-stage research pipeline.

When a user provides minimal input (name + industry + description),
this service runs automated research to pre-fill brand profile fields
and produce deliverable documents visible in Mission Control.

Stages:
  1. niche_analysis      — Industry/niche research, sub-niche identification
  2. audience_research    — Target audience demographics, pain points, goals
  3. competitive_intel    — Competitor analysis in the space
  4. content_landscape    — What content works in this niche
  5. voice_positioning    — Suggested voice DNA and market positioning
  6. content_strategy     — Content pillars and strategy recommendations
  7. content_ideas        — Initial content ideas based on all research

Each stage:
  - Runs web searches for real-time data
  - Uses LLM to synthesize findings into structured output
  - Saves results to the research session
  - Creates a deliverable in Mission Control (if agents are seeded)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.deps import get_admin_client
from app.services.web_search import search_web, search_linkedin, search_reddit

logger = logging.getLogger("app.services.brand_research")

# ── Stage Definitions ─────────────────────────────────────────

STAGES = [
    "niche_analysis",
    "audience_research",
    "competitive_intel",
    "content_landscape",
    "voice_positioning",
    "content_strategy",
    "content_ideas",
]

STAGE_LABELS = {
    "niche_analysis": "Niche Analysis",
    "audience_research": "Audience Research",
    "competitive_intel": "Competitive Intelligence",
    "content_landscape": "Content Landscape",
    "voice_positioning": "Voice & Positioning",
    "content_strategy": "Content Strategy",
    "content_ideas": "Content Ideas",
}


# ── Session Management ────────────────────────────────────────


def create_session(
    user_id: str,
    brand_id: str,
    seed_input: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new research session and return its row."""
    sb = get_admin_client()
    session_id = str(uuid.uuid4())
    row = {
        "id": session_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "seed_input": seed_input,
        "status": "pending",
        "current_stage": STAGES[0],
        "stages_completed": [],
        "results": {},
    }
    sb.table("brand_research_sessions").insert(row).execute()
    logger.info("Created research session %s for brand %s", session_id, brand_id)
    return row


def get_session(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a research session by ID."""
    sb = get_admin_client()
    resp = (
        sb.table("brand_research_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def get_sessions_for_brand(user_id: str, brand_id: str) -> List[Dict[str, Any]]:
    """List all research sessions for a brand."""
    sb = get_admin_client()
    resp = (
        sb.table("brand_research_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def _update_session(
    session_id: str,
    user_id: str,
    updates: Dict[str, Any],
) -> None:
    """Update a research session."""
    sb = get_admin_client()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    sb.table("brand_research_sessions").update(updates).eq("id", session_id).eq("user_id", user_id).execute()


# ── LLM Helper ────────────────────────────────────────────────


def _get_llm():
    """Get the LLM client."""
    from worker.graph.llm import get_llm_client
    return get_llm_client()


def _llm_call(
    system_prompt: str,
    user_prompt: str,
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    """Make an LLM call and return the content string.

    Retry logic is handled by the LLM client (llm.py) — no duplicate retries here.
    """
    if not model:
        from worker.graph.llm import get_model_for_chat
        model = get_model_for_chat()

    llm = _get_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = llm.chat(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response["content"]


def _llm_json_call(
    system_prompt: str,
    user_prompt: str,
    model: str = "",
    max_tokens: int = 4000,
) -> Dict[str, Any]:
    """Make an LLM call expecting JSON output."""
    from worker.graph.llm import parse_json_response
    raw = _llm_call(system_prompt, user_prompt, model=model, max_tokens=max_tokens)
    return parse_json_response(raw)


# ── Web Research Helper ───────────────────────────────────────


def _research(queries: List[str], max_per_query: int = 5) -> str:
    """Run multiple web searches and return combined context string."""
    all_results = []
    for q in queries:
        try:
            results = search_web(q, max_results=max_per_query)
            for r in results:
                all_results.append(f"- {r['title']}: {r['snippet']}")
        except Exception as e:
            logger.warning("Web search failed for query '%s': %s", q[:50], e)

    if not all_results:
        return "(No web results available — use your own knowledge)"

    return "\n".join(all_results[:30])  # Cap at 30 results


# ── Stage Runners ─────────────────────────────────────────────


def _run_niche_analysis(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 1: Research the industry/niche and identify sub-niches with TAM + ticket size."""
    name = seed.get("name", "")
    industry = seed.get("industry", "")
    description = seed.get("description", "")

    research_context = _research([
        f"{industry} niche market size TAM total addressable market 2025 2026",
        f"{industry} sub-niches personal branding opportunities ticket size pricing",
        f"best niches for personal brand {industry} revenue potential",
        f"{industry} coaching consulting service pricing average deal size",
    ])

    result = _llm_json_call(
        system_prompt=(
            "You are a niche analysis expert who also evaluates business viability. "
            "Analyze the industry and identify the best sub-niches for personal branding "
            "AND their revenue potential. Return JSON with these keys:\n"
            "- industry_overview: string (2-3 sentence overview)\n"
            "- market_size_trend: string (growing/stable/declining + context)\n"
            "- tam: string (Total Addressable Market estimate with source reasoning, e.g. '$4.2B globally')\n"
            "- tam_reasoning: string (how you estimated it)\n"
            "- ticket_size: object with {low: string, mid: string, high: string, typical: string} "
            "  (e.g. low='$97/mo', mid='$2,500 program', high='$25,000 retainer', typical='$3,000-8,000')\n"
            "- revenue_potential: string (estimated monthly revenue if person gets 3-10 clients)\n"
            "- agency_revenue_note: string (what a marketing agency managing this person could earn — "
            "  factor in lead gen, content retainer, and commissions)\n"
            "- sub_niches: array of {name, description, opportunity_score (1-10), reasoning, "
            "  typical_ticket_size: string, tam_slice: string}\n"
            "- recommended_niche: string (best sub-niche for this person)\n"
            "- recommended_niche_reasoning: string\n"
            "- key_trends: array of strings (3-5 trends)\n"
            "Return ONLY valid JSON."
        ),
        user_prompt=(
            f"Person: {name}\n"
            f"Industry: {industry}\n"
            f"Description: {description}\n\n"
            f"Web Research:\n{research_context}"
        ),
    )
    return result


def _run_audience_research(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 2: Research target audience demographics and pain points."""
    industry = seed.get("industry", "")
    description = seed.get("description", "")
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", industry)

    research_context = _research([
        f"{niche} target audience demographics pain points",
        f"{niche} ideal client avatar personal brand",
        f"what problems does {niche} audience have",
    ])

    reddit_context = search_reddit(f"{niche} struggles challenges help", max_results=5)
    reddit_text = "\n".join(f"- {r['title']}: {r['snippet']}" for r in reddit_context) or "(none)"

    result = _llm_json_call(
        system_prompt=(
            "You are an audience research expert. Research the target audience for "
            "this niche. Return JSON with:\n"
            "- primary_audience: {age_range, gender_split, income_level, education, location}\n"
            "- psychographics: {values: [], motivations: [], fears: [], aspirations: []}\n"
            "- pain_points: array of {pain_point, severity (1-10), context}\n"
            "- goals: array of strings (what they want to achieve)\n"
            "- where_they_hang_out: array of {platform, description}\n"
            "- buying_triggers: array of strings\n"
            "- objections: array of strings\n"
            "Return ONLY valid JSON."
        ),
        user_prompt=(
            f"Niche: {niche}\n"
            f"Description: {description}\n\n"
            f"Web Research:\n{research_context}\n\n"
            f"Reddit Discussions:\n{reddit_text}"
        ),
    )
    return result


def _run_competitive_intel(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 3: Research competitors in the space."""
    industry = seed.get("industry", "")
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", industry)

    research_context = _research([
        f"top personal brands {niche}",
        f"{niche} thought leaders influencers",
        f"best {niche} content creators",
    ])

    linkedin_results = search_linkedin(f"{niche} personal brand", max_results=5)
    linkedin_text = "\n".join(f"- {r['title']}: {r['snippet']}" for r in linkedin_results) or "(none)"

    result = _llm_json_call(
        system_prompt=(
            "You are a competitive intelligence analyst. Identify and analyze key "
            "competitors/thought leaders in this niche. Return JSON with:\n"
            "- competitors: array of {name, platform, followers_estimate, niche_focus, "
            "content_style, strengths: [], weaknesses: [], key_differentiator}\n"
            "- market_gaps: array of {gap, opportunity, difficulty (easy/medium/hard)}\n"
            "- differentiation_opportunities: array of strings\n"
            "- competitive_landscape: string (summary paragraph)\n"
            "Return ONLY valid JSON. List 5-8 competitors."
        ),
        user_prompt=(
            f"Niche: {niche}\n\n"
            f"Web Research:\n{research_context}\n\n"
            f"LinkedIn:\n{linkedin_text}"
        ),
    )
    return result


def _run_content_landscape(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 4: Research what content works in this niche."""
    industry = seed.get("industry", "")
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", industry)

    research_context = _research([
        f"best performing content {niche} social media",
        f"{niche} content strategy what works",
        f"viral content {niche} examples",
    ])

    result = _llm_json_call(
        system_prompt=(
            "You are a content strategy analyst. Research what content works best "
            "in this niche. Return JSON with:\n"
            "- top_formats: array of {format, effectiveness (1-10), platforms: [], example}\n"
            "- top_topics: array of {topic, engagement_level (high/medium/low), why_it_works}\n"
            "- posting_patterns: {best_times: [], frequency_recommendation, platform_priority: []}\n"
            "- hook_styles: array of {style, example, effectiveness}\n"
            "- content_gaps: array of {topic, opportunity, difficulty}\n"
            "- trending_formats: array of strings\n"
            "Return ONLY valid JSON."
        ),
        user_prompt=(
            f"Niche: {niche}\n\n"
            f"Web Research:\n{research_context}"
        ),
    )
    return result


def _run_voice_positioning(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 5: Suggest voice DNA and market positioning."""
    name = seed.get("name", "")
    description = seed.get("description", "")
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", seed.get("industry", ""))
    audience = prior_results.get("audience_research", {})
    competitors = prior_results.get("competitive_intel", {})

    audience_summary = json.dumps(audience.get("psychographics", {}), default=str)[:500]
    gaps = json.dumps(competitors.get("market_gaps", []), default=str)[:500]

    result = _llm_json_call(
        system_prompt=(
            "You are a brand positioning expert. Based on the research so far, "
            "suggest voice DNA and market positioning. Return JSON with:\n"
            "- voice_options: array of 3 objects, each with:\n"
            "  {name, description, tone_words: [5 words], example_post, "
            "  audience_fit_score (1-10), differentiation_score (1-10)}\n"
            "- recommended_voice: string (name of recommended option)\n"
            "- recommended_voice_reasoning: string\n"
            "- positioning_statement: string (1-2 sentence positioning)\n"
            "- unique_angle: string (what makes this person different)\n"
            "- it_factor: string (their unique strength/perspective)\n"
            "- brand_personality: {adjectives: [5], archetype, description}\n"
            "Return ONLY valid JSON."
        ),
        user_prompt=(
            f"Person: {name}\n"
            f"Description: {description}\n"
            f"Niche: {niche}\n"
            f"Audience Psychographics: {audience_summary}\n"
            f"Market Gaps: {gaps}"
        ),
    )
    return result


def _run_content_strategy(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 6: Generate content pillars and strategy."""
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", seed.get("industry", ""))
    audience = prior_results.get("audience_research", {})
    content = prior_results.get("content_landscape", {})
    voice = prior_results.get("voice_positioning", {})

    pain_points = json.dumps(audience.get("pain_points", []), default=str)[:400]
    top_formats = json.dumps(content.get("top_formats", []), default=str)[:400]
    voice_name = voice.get("recommended_voice", "")

    result = _llm_json_call(
        system_prompt=(
            "You are a content strategy architect. Design a complete content strategy "
            "based on all research. Return JSON with:\n"
            "- content_pillars: array of 4-5 objects, each with:\n"
            "  {name, description, audience_pain_point, content_ratio (%), "
            "  example_topics: [3], formats: [2]}\n"
            "- content_mix: {educational_pct, inspirational_pct, promotional_pct, "
            "  entertainment_pct, community_pct}\n"
            "- posting_cadence: {posts_per_week, platform_split: {platform: posts}}\n"
            "- growth_strategy: {phase_1_weeks_1_4: string, phase_2_weeks_5_8: string, "
            "  phase_3_weeks_9_12: string}\n"
            "- cta_strategy: string (how to convert followers to leads)\n"
            "- measurement_kpis: array of {metric, target, why}\n"
            "Return ONLY valid JSON."
        ),
        user_prompt=(
            f"Niche: {niche}\n"
            f"Voice: {voice_name}\n"
            f"Audience Pain Points: {pain_points}\n"
            f"Top Formats: {top_formats}"
        ),
    )
    return result


def _run_content_ideas(seed: Dict[str, Any], prior_results: Dict) -> Dict[str, Any]:
    """Stage 7: Generate initial content ideas based on all research."""
    niche = prior_results.get("niche_analysis", {}).get("recommended_niche", seed.get("industry", ""))
    pillars = prior_results.get("content_strategy", {}).get("content_pillars", [])
    hooks = prior_results.get("content_landscape", {}).get("hook_styles", [])
    voice = prior_results.get("voice_positioning", {}).get("recommended_voice", "")

    pillars_text = json.dumps(pillars, default=str)[:600]
    hooks_text = json.dumps(hooks, default=str)[:300]

    result = _llm_json_call(
        system_prompt=(
            "You are a creative content strategist. Generate 10 specific content ideas "
            "that this person can create immediately. Return JSON with:\n"
            "- content_ideas: array of 10 objects, each with:\n"
            "  {title, hook, pillar, format (carousel/post/video/story/thread), "
            "  platform, estimated_engagement (high/medium/low), brief (2-3 sentences), "
            "  cta}\n"
            "- quick_wins: array of 3 strings (easiest content to create first)\n"
            "- content_calendar_week_1: array of 5 objects with {day, title, format, platform}\n"
            "Return ONLY valid JSON. Make ideas specific and actionable, not generic."
        ),
        user_prompt=(
            f"Niche: {niche}\n"
            f"Voice: {voice}\n"
            f"Content Pillars: {pillars_text}\n"
            f"Hook Styles: {hooks_text}"
        ),
    )
    return result


# ── Stage Registry ────────────────────────────────────────────

STAGE_RUNNERS = {
    "niche_analysis": _run_niche_analysis,
    "audience_research": _run_audience_research,
    "competitive_intel": _run_competitive_intel,
    "content_landscape": _run_content_landscape,
    "voice_positioning": _run_voice_positioning,
    "content_strategy": _run_content_strategy,
    "content_ideas": _run_content_ideas,
}


# ── Pipeline Orchestrator ─────────────────────────────────────


def run_stage(session_id: str, user_id: str) -> Dict[str, Any]:
    """Run the next pending stage for a research session.

    Returns the updated session dict.
    Raises ValueError if session not found or already completed.
    """
    session = get_session(session_id, user_id)
    if not session:
        raise ValueError(f"Research session {session_id} not found")

    if session["status"] == "completed":
        raise ValueError("Research session already completed")

    # ── Optimistic concurrency lock ───────────────────────────────────────
    # If another request is already running this session, skip execution instead
    # of double-running a stage. This prevents race conditions when the client
    # polls aggressively or retries mid-flight.
    if session["status"] == "running":
        logger.info(
            "Research session %s is already running stage '%s' — skipping concurrent execution",
            session_id, session.get("current_stage", "unknown"),
        )
        return session

    if session["status"] == "failed":
        # Allow retry — reset to running so the failed stage can re-run
        _update_session(session_id, user_id, {
            "status": "running",
            "error": None,
        })

    # Determine which stage to run
    completed = session.get("stages_completed") or []
    current_stage = None
    for stage in STAGES:
        if stage not in completed:
            current_stage = stage
            break

    if current_stage is None:
        # All stages done
        _update_session(session_id, user_id, {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        return get_session(session_id, user_id)

    # Mark running
    _update_session(session_id, user_id, {
        "status": "running",
        "current_stage": current_stage,
        "started_at": session.get("started_at") or datetime.now(timezone.utc).isoformat(),
    })

    runner = STAGE_RUNNERS[current_stage]
    seed = session.get("seed_input", {})
    prior_results = session.get("results", {})

    try:
        stage_result = runner(seed, prior_results)
    except Exception as e:
        error_type = type(e).__name__
        if "Connection" in error_type or "Timeout" in error_type:
            error_detail = "AI service temporarily unavailable. Please try again in a moment."
        else:
            error_detail = f"{error_type}: {str(e)[:400]}"
        logger.error("Stage %s failed for session %s: [%s] %s", current_stage, session_id, error_type, e)
        _update_session(session_id, user_id, {
            "status": "failed",
            "error": f"Stage {current_stage} failed: {error_detail}",
        })
        raise

    # Save results
    results = session.get("results", {}) or {}
    results[current_stage] = stage_result
    new_completed = completed + [current_stage]

    # Check if this was the last stage
    all_done = len(new_completed) == len(STAGES)

    _update_session(session_id, user_id, {
        "results": results,
        "stages_completed": new_completed,
        "current_stage": STAGES[STAGES.index(current_stage) + 1] if not all_done else current_stage,
        "status": "completed" if all_done else "pending",
        "completed_at": datetime.now(timezone.utc).isoformat() if all_done else None,
    })

    # Create deliverable for this stage
    _create_stage_deliverable(session_id, user_id, session["brand_id"], current_stage, stage_result)

    logger.info(
        "Stage %s completed for session %s (%d/%d)",
        current_stage, session_id, len(new_completed), len(STAGES),
    )

    return get_session(session_id, user_id)


def run_all_stages(session_id: str, user_id: str) -> Dict[str, Any]:
    """Run all remaining stages sequentially. Returns final session."""
    for _ in range(len(STAGES)):
        session = get_session(session_id, user_id)
        if not session or session["status"] in ("completed", "failed", "cancelled"):
            break
        run_stage(session_id, user_id)

    return get_session(session_id, user_id)


def skip_stage(session_id: str, user_id: str) -> Dict[str, Any]:
    """Skip the current failed/pending stage and advance to the next one.

    Marks the skipped stage as completed with empty results so the pipeline
    can continue. Returns the updated session.
    """
    session = get_session(session_id, user_id)
    if not session:
        raise ValueError(f"Research session {session_id} not found")

    if session["status"] == "completed":
        raise ValueError("Research session already completed")

    # Determine which stage to skip
    completed = session.get("stages_completed") or []
    current_stage = None
    for stage in STAGES:
        if stage not in completed:
            current_stage = stage
            break

    if current_stage is None:
        raise ValueError("No stages left to skip")

    # Mark skipped with empty results
    results = session.get("results", {}) or {}
    results[current_stage] = {"_skipped": True}
    new_completed = completed + [current_stage]
    all_done = len(new_completed) == len(STAGES)

    update = {
        "results": results,
        "stages_completed": new_completed,
        "status": "completed" if all_done else "pending",
        "error": None,
    }
    if not all_done:
        next_idx = STAGES.index(current_stage) + 1
        update["current_stage"] = STAGES[next_idx]
    if all_done:
        update["completed_at"] = datetime.now(timezone.utc).isoformat()

    _update_session(session_id, user_id, update)

    logger.info("Stage %s skipped for session %s", current_stage, session_id)
    return get_session(session_id, user_id)


# ── Deliverable Creation ──────────────────────────────────────


def _create_stage_deliverable(
    session_id: str,
    user_id: str,
    brand_id: str,
    stage: str,
    result: Dict[str, Any],
) -> None:
    """Create a Mission Control deliverable for a completed research stage."""
    sb = get_admin_client()

    label = STAGE_LABELS.get(stage, stage)
    content_text = _format_stage_report(stage, result)

    try:
        sb.table("agent_deliverables").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "task_id": session_id,  # Link to research session
            "title": f"Brand Research: {label}",
            "content": content_text,
            "deliverable_type": "report",
            "status": "review",
            "feedback": None,
            "created_by_agent_id": None,  # System-generated
        }).execute()
    except Exception as e:
        # Non-fatal: deliverable creation shouldn't block research
        logger.warning("Failed to create deliverable for stage %s: %s", stage, e)


def _format_stage_report(stage: str, result: Dict[str, Any]) -> str:
    """Format a stage result as a readable report."""
    label = STAGE_LABELS.get(stage, stage)
    lines = [f"# {label} Report\n"]

    if stage == "niche_analysis":
        lines.append(f"**Industry Overview:** {result.get('industry_overview', 'N/A')}\n")
        lines.append(f"**Market Trend:** {result.get('market_size_trend', 'N/A')}\n")
        lines.append(f"**Recommended Niche:** {result.get('recommended_niche', 'N/A')}")
        lines.append(f"**Reasoning:** {result.get('recommended_niche_reasoning', 'N/A')}\n")
        for niche in result.get("sub_niches", []):
            lines.append(f"- **{niche.get('name', '?')}** (Score: {niche.get('opportunity_score', '?')}/10): {niche.get('description', '')}")
        trends = result.get("key_trends", [])
        if trends:
            lines.append("\n**Key Trends:**")
            for t in trends:
                lines.append(f"- {t}")

    elif stage == "audience_research":
        primary = result.get("primary_audience", {})
        lines.append(f"**Age Range:** {primary.get('age_range', 'N/A')}")
        lines.append(f"**Income Level:** {primary.get('income_level', 'N/A')}\n")
        for pp in result.get("pain_points", []):
            lines.append(f"- **Pain Point** (Severity {pp.get('severity', '?')}/10): {pp.get('pain_point', '')}")
        goals = result.get("goals", [])
        if goals:
            lines.append("\n**Goals:**")
            for g in goals:
                lines.append(f"- {g}")

    elif stage == "competitive_intel":
        lines.append(f"**Landscape:** {result.get('competitive_landscape', 'N/A')}\n")
        for comp in result.get("competitors", []):
            lines.append(f"- **{comp.get('name', '?')}** ({comp.get('platform', '?')}): {comp.get('key_differentiator', '')}")
        gaps = result.get("market_gaps", [])
        if gaps:
            lines.append("\n**Market Gaps:**")
            for g in gaps:
                lines.append(f"- {g.get('gap', '')}: {g.get('opportunity', '')} [{g.get('difficulty', '?')}]")

    elif stage == "content_landscape":
        for fmt in result.get("top_formats", []):
            lines.append(f"- **{fmt.get('format', '?')}** (Effectiveness: {fmt.get('effectiveness', '?')}/10)")
        hooks = result.get("hook_styles", [])
        if hooks:
            lines.append("\n**Hook Styles:**")
            for h in hooks:
                lines.append(f"- **{h.get('style', '?')}**: \"{h.get('example', '')}\"")

    elif stage == "voice_positioning":
        lines.append(f"**Positioning:** {result.get('positioning_statement', 'N/A')}")
        lines.append(f"**IT Factor:** {result.get('it_factor', 'N/A')}\n")
        for v in result.get("voice_options", []):
            lines.append(f"### Voice Option: {v.get('name', '?')}")
            lines.append(f"{v.get('description', '')}")
            lines.append(f"Tone: {', '.join(v.get('tone_words', []))}")
            lines.append(f"Example: \"{v.get('example_post', '')}\"")
            lines.append(f"Fit: {v.get('audience_fit_score', '?')}/10 | Differentiation: {v.get('differentiation_score', '?')}/10\n")
        lines.append(f"**Recommended:** {result.get('recommended_voice', 'N/A')}")

    elif stage == "content_strategy":
        for pillar in result.get("content_pillars", []):
            lines.append(f"### {pillar.get('name', '?')} ({pillar.get('content_ratio', '?')}%)")
            lines.append(f"{pillar.get('description', '')}")
            lines.append(f"Addresses: {pillar.get('audience_pain_point', '')}")
            topics = pillar.get("example_topics", [])
            if topics:
                for t in topics:
                    lines.append(f"  - {t}")
            lines.append("")
        growth = result.get("growth_strategy", {})
        if growth:
            lines.append("**Growth Strategy:**")
            lines.append(f"- Weeks 1-4: {growth.get('phase_1_weeks_1_4', 'N/A')}")
            lines.append(f"- Weeks 5-8: {growth.get('phase_2_weeks_5_8', 'N/A')}")
            lines.append(f"- Weeks 9-12: {growth.get('phase_3_weeks_9_12', 'N/A')}")

    elif stage == "content_ideas":
        for idea in result.get("content_ideas", []):
            lines.append(f"### {idea.get('title', '?')}")
            lines.append(f"**Hook:** {idea.get('hook', '')}")
            lines.append(f"**Format:** {idea.get('format', '?')} | **Platform:** {idea.get('platform', '?')}")
            lines.append(f"{idea.get('brief', '')}\n")
        qw = result.get("quick_wins", [])
        if qw:
            lines.append("**Quick Wins (Start Here):**")
            for w in qw:
                lines.append(f"1. {w}")

    else:
        lines.append(json.dumps(result, indent=2, default=str))

    return "\n".join(lines)


# ── Profile Pre-fill ──────────────────────────────────────────


def apply_research_to_profile(session_id: str, user_id: str, brand_id: str) -> Dict[str, Any]:
    """Apply research results to pre-fill brand profile fields.

    Only fills fields that are currently empty. Never overwrites
    user-entered data. Returns dict of fields that were pre-filled.
    """
    session = get_session(session_id, user_id)
    if not session or session["status"] != "completed":
        raise ValueError("Research session not completed")

    sb = get_admin_client()
    brand_resp = (
        sb.table("personal_brands")
        .select("profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_resp.data:
        raise ValueError("Brand not found")

    profile = brand_resp.data[0].get("profile_json") or {}
    results = session.get("results", {})
    prefilled = {}

    # Map research results to brand profile fields
    niche = results.get("niche_analysis", {})
    audience = results.get("audience_research", {})
    competitors = results.get("competitive_intel", {})
    voice = results.get("voice_positioning", {})
    strategy = results.get("content_strategy", {})

    # Foundation module
    foundation = profile.get("foundation", {}) or {}
    if not foundation.get("industry") and niche.get("recommended_niche"):
        foundation["industry"] = niche["recommended_niche"]
        prefilled["foundation.industry"] = niche["recommended_niche"]
    profile["foundation"] = foundation

    # ICA module
    ica = profile.get("ica", {}) or {}
    primary_aud = audience.get("primary_audience", {})
    if not ica.get("age_range") and primary_aud.get("age_range"):
        ica["age_range"] = primary_aud["age_range"]
        prefilled["ica.age_range"] = primary_aud["age_range"]
    pain_points = audience.get("pain_points", [])
    if not ica.get("pain_points") and pain_points:
        pp_text = "; ".join(p.get("pain_point", "") for p in pain_points[:5])
        ica["pain_points"] = pp_text
        prefilled["ica.pain_points"] = pp_text
    goals = audience.get("goals", [])
    if not ica.get("goals") and goals:
        ica["goals"] = "; ".join(goals[:5])
        prefilled["ica.goals"] = "; ".join(goals[:5])
    hangouts = audience.get("where_they_hang_out", [])
    if not ica.get("where_they_hang_out") and hangouts:
        ica["where_they_hang_out"] = "; ".join(h.get("platform", "") for h in hangouts[:5])
        prefilled["ica.where_they_hang_out"] = ica["where_they_hang_out"]
    profile["ica"] = ica

    # Competitors module
    comp = profile.get("competitors", {}) or {}
    comp_list = competitors.get("competitors", [])
    if not comp.get("competitors") and comp_list:
        comp["competitors"] = json.dumps(comp_list[:5], default=str)
        prefilled["competitors.competitors"] = comp["competitors"]
    gaps = competitors.get("market_gaps", [])
    if not comp.get("market_gaps") and gaps:
        comp["market_gaps"] = json.dumps(gaps[:5], default=str)
        prefilled["competitors.market_gaps"] = comp["market_gaps"]
    profile["competitors"] = comp

    # Messaging module (voice DNA)
    messaging = profile.get("messaging", {}) or {}
    recommended = voice.get("recommended_voice", "")
    voice_options = voice.get("voice_options", [])
    matching_voice = next((v for v in voice_options if v.get("name") == recommended), None)
    if not messaging.get("tone_words") and matching_voice:
        messaging["tone_words"] = matching_voice.get("tone_words", [])
        prefilled["messaging.tone_words"] = messaging["tone_words"]
    if not messaging.get("voice_description") and matching_voice:
        messaging["voice_description"] = matching_voice.get("description", "")
        prefilled["messaging.voice_description"] = messaging["voice_description"]
    profile["messaging"] = messaging

    # Positioning module
    positioning = profile.get("positioning", {}) or {}
    if not positioning.get("positioning_statement") and voice.get("positioning_statement"):
        positioning["positioning_statement"] = voice["positioning_statement"]
        prefilled["positioning.positioning_statement"] = voice["positioning_statement"]
    if not positioning.get("it_factor") and voice.get("it_factor"):
        positioning["it_factor"] = voice["it_factor"]
        prefilled["positioning.it_factor"] = voice["it_factor"]
    if not positioning.get("unique_angle") and voice.get("unique_angle"):
        positioning["unique_angle"] = voice["unique_angle"]
        prefilled["positioning.unique_angle"] = voice["unique_angle"]
    profile["positioning"] = positioning

    # Save updated profile
    if prefilled:
        sb.table("personal_brands").update({
            "profile_json": profile,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", brand_id).eq("user_id", user_id).execute()

        logger.info(
            "Pre-filled %d fields for brand %s from research %s",
            len(prefilled), brand_id, session_id,
        )

    return prefilled
