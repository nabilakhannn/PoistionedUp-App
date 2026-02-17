"""Real-time research aggregator.

Combines web search, YouTube trends, Reddit discussions, and competitor
analysis into structured research signals for the content pipeline
and brand coaching chat.

Usage:
    from app.services.research import run_research, format_research_for_prompt

    signals = run_research(
        topic="personal branding for coaches",
        sources={"web": True, "youtube": True, "reddit": True},
    )
    context = format_research_for_prompt(signals)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("app.services.research")


def run_research(
    topic: str,
    sources: Optional[Dict[str, bool]] = None,
    competitor_urls: Optional[List[str]] = None,
    max_web_results: int = 8,
    max_youtube_results: int = 5,
    max_reddit_results: int = 5,
) -> Dict[str, Any]:
    """Run real-time research across multiple sources.

    Args:
        topic: The research topic or query
        sources: Which sources to use (web, youtube, reddit). All on by default.
        competitor_urls: Specific URLs to analyze
        max_web_results: Max web search results
        max_youtube_results: Max YouTube results
        max_reddit_results: Max Reddit results

    Returns dict with:
        - web_results: list of web search results
        - youtube_trends: list of YouTube video results
        - reddit_discussions: list of Reddit post results
        - competitor_analysis: list of analyzed competitor URLs
        - summary: formatted text summary of all findings
        - signal_count: total number of signals found
    """
    if sources is None:
        sources = {"web": True, "youtube": True, "reddit": True}

    from app.services.web_search import (
        search_web,
        search_youtube_trends,
        search_reddit,
        analyze_competitor_url,
    )

    results: Dict[str, Any] = {
        "web_results": [],
        "youtube_trends": [],
        "reddit_discussions": [],
        "competitor_analysis": [],
        "signal_count": 0,
    }

    # Web search: trending content + audience pain points
    if sources.get("web", True):
        try:
            web_results = search_web(
                f"{topic} trends tips 2026",
                max_results=max_web_results,
            )
            results["web_results"] = web_results
            results["signal_count"] += len(web_results)
        except Exception as e:
            logger.warning("Web search failed: %s", e)

        # Also search for audience pain points
        try:
            pain_results = search_web(
                f"{topic} problems challenges struggles",
                max_results=max_web_results // 2,
            )
            results["web_results"].extend(pain_results)
            results["signal_count"] += len(pain_results)
        except Exception as e:
            logger.warning("Pain point search failed: %s", e)

    # YouTube: what's getting views in this space
    if sources.get("youtube", True):
        try:
            yt_results = search_youtube_trends(
                topic,
                max_results=max_youtube_results,
            )
            results["youtube_trends"] = yt_results
            results["signal_count"] += len(yt_results)
        except Exception as e:
            logger.warning("YouTube search failed: %s", e)

    # Reddit: what people are actually talking about
    if sources.get("reddit", True):
        try:
            reddit_results = search_reddit(
                topic,
                max_results=max_reddit_results,
            )
            results["reddit_discussions"] = reddit_results
            results["signal_count"] += len(reddit_results)
        except Exception as e:
            logger.warning("Reddit search failed: %s", e)

    # Competitor URL analysis
    if competitor_urls:
        for url in competitor_urls[:5]:  # Cap at 5 URLs
            try:
                analysis = analyze_competitor_url(url)
                if analysis.get("text"):
                    results["competitor_analysis"].append(analysis)
                    results["signal_count"] += 1
            except Exception as e:
                logger.warning("Competitor analysis failed for %s: %s", url, e)

    # Build summary
    results["summary"] = _build_summary(results)

    logger.info(
        "Research complete: %d total signals for '%s'",
        results["signal_count"], topic[:50],
    )
    return results


def _build_summary(results: Dict[str, Any]) -> str:
    """Build a human-readable summary of research findings."""
    parts = []

    web = results.get("web_results", [])
    if web:
        parts.append(f"Found {len(web)} web articles/posts on this topic.")

    yt = results.get("youtube_trends", [])
    if yt:
        parts.append(f"Found {len(yt)} recent YouTube videos in this space.")

    reddit = results.get("reddit_discussions", [])
    if reddit:
        parts.append(f"Found {len(reddit)} Reddit discussions about this.")

    comp = results.get("competitor_analysis", [])
    if comp:
        parts.append(f"Analyzed {len(comp)} competitor content pieces.")

    if not parts:
        return "No real-time research data available."

    return " ".join(parts)


def format_research_for_prompt(
    research: Dict[str, Any],
    max_chars: int = 4000,
) -> str:
    """Format research results into a context block for LLM prompts.

    Keeps it under max_chars to avoid blowing up the context window.
    """
    sections = []

    # Web results
    web = research.get("web_results", [])
    if web:
        lines = ["## Live Web Research"]
        for r in web[:8]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")[:200]
            url = r.get("url", "")
            if title:
                lines.append(f"- **{title}**")
                if snippet:
                    lines.append(f"  {snippet}")
                if url:
                    lines.append(f"  Source: {url}")
        sections.append("\n".join(lines))

    # YouTube trends
    yt = research.get("youtube_trends", [])
    if yt:
        lines = ["## Trending YouTube Content"]
        for r in yt[:5]:
            title = r.get("title", "")
            publisher = r.get("publisher", "")
            views = r.get("views", "")
            desc = r.get("description", "")[:150]
            if title:
                line = f"- **{title}**"
                if publisher:
                    line += f" by {publisher}"
                if views:
                    line += f" ({views} views)"
                lines.append(line)
                if desc:
                    lines.append(f"  {desc}")
        sections.append("\n".join(lines))

    # Reddit discussions
    reddit = research.get("reddit_discussions", [])
    if reddit:
        lines = ["## Reddit Discussions"]
        for r in reddit[:5]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")[:150]
            if title:
                lines.append(f"- {title}")
                if snippet:
                    lines.append(f"  {snippet}")
        sections.append("\n".join(lines))

    # Competitor analysis
    comp = research.get("competitor_analysis", [])
    if comp:
        lines = ["## Competitor Content"]
        for r in comp[:3]:
            url = r.get("url", "")
            text = r.get("text", "")[:500]
            source_type = r.get("source_type", "webpage")
            lines.append(f"- [{source_type}] {url}")
            if text:
                lines.append(f"  Content excerpt: {text[:300]}...")
        sections.append("\n".join(lines))

    if not sections:
        return ""

    full_text = (
        "--- REAL-TIME RESEARCH DATA (live from the web) ---\n"
        "Use this data to ground your coaching in current market reality. "
        "Reference specific trends, competitors, or discussions when relevant.\n\n"
        + "\n\n".join(sections)
    )

    # Truncate if too long
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n[Research truncated for context limits]"

    return full_text


def format_research_as_signals(
    research: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert research results into structured signal dicts for the pipeline.

    Each signal has: type, title, description, source, relevance_score, evidence
    """
    signals = []

    # Web results -> trend/pain_point signals
    for r in research.get("web_results", []):
        signals.append({
            "type": "trend",
            "title": r.get("title", "Untitled"),
            "description": r.get("snippet", ""),
            "source": r.get("url", "web search"),
            "relevance_score": 7,  # Default, LLM will re-score
            "evidence": f"Found via web search: {r.get('snippet', '')[:200]}",
            "live_data": True,
        })

    # YouTube results -> outlier signals
    for r in research.get("youtube_trends", []):
        views_str = r.get("views", "")
        signals.append({
            "type": "outlier",
            "title": r.get("title", "Untitled"),
            "description": r.get("description", ""),
            "source": r.get("url", "YouTube"),
            "relevance_score": 7,
            "evidence": f"YouTube video by {r.get('publisher', 'unknown')}"
                        + (f", {views_str} views" if views_str else ""),
            "live_data": True,
        })

    # Reddit results -> pain_point signals
    for r in research.get("reddit_discussions", []):
        signals.append({
            "type": "pain_point",
            "title": r.get("title", "Untitled"),
            "description": r.get("snippet", ""),
            "source": r.get("url", "Reddit"),
            "relevance_score": 6,
            "evidence": f"Reddit discussion: {r.get('snippet', '')[:200]}",
            "live_data": True,
        })

    # Competitor analysis -> competitor signals
    for r in research.get("competitor_analysis", []):
        signals.append({
            "type": "competitor",
            "title": f"Competitor content: {r.get('source_type', 'webpage')}",
            "description": r.get("text", "")[:300],
            "source": r.get("url", "competitor"),
            "relevance_score": 8,
            "evidence": f"Analyzed from: {r.get('url', '')}",
            "live_data": True,
        })

    return signals
