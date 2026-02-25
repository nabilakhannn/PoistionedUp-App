"""Node 1: Signal research — find trending topics, pain points, and gaps.

This node now combines REAL-TIME web research with LLM analysis.
Live data from web search, YouTube trends, and Reddit discussions
is fed into the LLM prompt so the model works with actual market
signals instead of generating them from memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response, set_tracking_context, safe_node
from worker.graph.prompts import signal_research as prompts

logger = logging.getLogger("worker.graph.nodes.signal_research")


def _format_ica(profile: Dict[str, Any]) -> str:
    """Extract ICA data from profile and format for the prompt."""
    ica = profile.get("ica", {})
    if not ica:
        return "No ICA defined yet."

    parts = []
    demo = ica.get("demographics", {})
    if demo:
        parts.append(f"Target: {demo.get('occupation', 'Unknown')} "
                      f"({demo.get('location', 'Unknown')})")
    if ica.get("big_need"):
        parts.append(f"Big need: {ica['big_need']}")
    if ica.get("big_want"):
        parts.append(f"Big want: {ica['big_want']}")
    if ica.get("pains"):
        pain_strs = [p.get("pain", "") for p in ica["pains"] if p.get("pain")]
        if pain_strs:
            parts.append(f"Key pains: {', '.join(pain_strs)}")
    if ica.get("desires"):
        desire_strs = [d.get("desire", "") for d in ica["desires"] if d.get("desire")]
        if desire_strs:
            parts.append(f"Key desires: {', '.join(desire_strs)}")
    bm = ica.get("buying_motivations", {})
    if bm:
        motives = [f"{k}: {v}" for k, v in bm.items() if v]
        if motives:
            parts.append(f"Buying motivations: {', '.join(motives)}")

    return "\n".join(parts) if parts else "No ICA defined yet."


def _format_offer(profile: Dict[str, Any]) -> str:
    """Extract offer data from profile and format for the prompt."""
    offer = profile.get("offer", {})
    if not offer:
        return "No offer defined yet."

    parts = []
    if offer.get("what"):
        parts.append(f"Offer: {offer['what']}")
    if offer.get("target_audience"):
        parts.append(f"Target audience: {offer['target_audience']}")
    if offer.get("differentiator"):
        parts.append(f"Differentiator: {offer['differentiator']}")

    brand = profile.get("brand", {})
    if brand.get("statement"):
        parts.append(f"Brand statement: {brand['statement']}")
    if brand.get("content_pillars"):
        parts.append(f"Content pillars: {', '.join(brand['content_pillars'])}")

    market = offer.get("market", {})
    if market.get("niche_statement"):
        parts.append(f"Niche: {market['niche_statement']}")
    if market.get("massive_pains"):
        parts.append(f"Market pains: {', '.join(market['massive_pains'])}")

    return "\n".join(parts) if parts else "No offer defined yet."


def _fetch_live_research(
    goal_text: str,
    profile: Dict[str, Any],
    sources: Dict[str, Any],
) -> str:
    """Fetch real-time research data from the web.

    Returns formatted context string to inject into the LLM prompt.
    """
    try:
        from app.services.research import run_research, format_research_for_prompt

        # Build the search query from goal + profile context
        topic_parts = [goal_text]

        # Add niche/industry context from profile
        offer = profile.get("offer", {})
        market = offer.get("market", {})
        if market.get("niche_statement"):
            topic_parts.append(market["niche_statement"])
        elif offer.get("target_audience"):
            topic_parts.append(offer["target_audience"])

        brand = profile.get("brand", {})
        if brand.get("content_pillars"):
            topic_parts.extend(brand["content_pillars"][:2])

        topic = " ".join(topic_parts[:3])  # Don't make query too long

        # Determine which sources to use
        research_sources = {
            "web": sources.get("web_search", True),
            "youtube": sources.get("youtube", True),
            "reddit": sources.get("reddit", True),
        }

        # Competitor URLs if configured
        competitor_urls = sources.get("competitor_channels", [])
        if isinstance(competitor_urls, str):
            competitor_urls = [u.strip() for u in competitor_urls.split(",") if u.strip()]

        research = run_research(
            topic=topic,
            sources=research_sources,
            competitor_urls=competitor_urls if competitor_urls else None,
            max_web_results=8,
            max_youtube_results=5,
            max_reddit_results=5,
        )

        formatted = format_research_for_prompt(research)
        if formatted:
            logger.info(
                "Live research returned %d signals for '%s'",
                research.get("signal_count", 0), topic[:50],
            )
        return formatted

    except Exception as e:
        logger.warning("Live research failed (will use LLM knowledge only): %s", e)
        return ""


@safe_node
def signal_research(state: Dict[str, Any]) -> Dict[str, Any]:
    """Research signals across configured sources.

    FLOW:
    1. Fetch real-time data from web, YouTube, Reddit
    2. Pass live data + creator profile to LLM
    3. LLM analyzes and ranks signals using REAL market data
    """
    _tier = state.get("settings", {}).get("model_tier", "")
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "signal_research", _tier)

    goal_text = state["goal_text"]
    profile = state.get("profile_snapshot", {})
    settings = state.get("settings", {})
    sources = settings.get("sources", {})

    # Format enabled sources for the prompt
    enabled = [k for k, v in sources.items() if v and k != "competitor_channels"]
    if sources.get("competitor_channels"):
        enabled.append(f"competitor_channels: {sources['competitor_channels']}")
    sources_str = ", ".join(enabled) if enabled else "general web research"

    # ── FETCH LIVE RESEARCH DATA ──
    live_context = _fetch_live_research(goal_text, profile, sources)

    # Build the user prompt with live data injected
    user_prompt = prompts.USER.format(
        goal_text=goal_text,
        profile=json.dumps(profile, indent=2),
        ica_context=_format_ica(profile),
        offer_context=_format_offer(profile),
        sources=sources_str,
    )

    if live_context:
        user_prompt += f"\n\n{live_context}"
        user_prompt += (
            "\n\nIMPORTANT: The research data above is LIVE from the web. "
            "Use it to ground your signal analysis in real, current market data. "
            "Reference specific articles, videos, or discussions in your evidence fields. "
            "Combine live data with your own knowledge to identify the best opportunities."
        )

    llm = get_llm_client()
    resp = llm.chat(
        messages=[
            {"role": "system", "content": prompts.SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model=get_model_for_step("signal_research"),
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(resp["content"])
    signals = result.get("signals", [])

    logger.info(
        "signal_research: found %d signals for goal=%s (live_data=%s)",
        len(signals), goal_text[:50], bool(live_context),
    )

    return {
        "research_signals": signals,
        "current_step": "signal_research",
        "research_live_data": bool(live_context),
    }
