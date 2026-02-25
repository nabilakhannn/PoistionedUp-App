"""Web search service for real-time research.

Provides live web search using multiple backends:
  - Tavily (preferred, needs TAVILY_API_KEY) — cleanest results for LLM apps
  - DuckDuckGo (free fallback, no API key needed)

Also provides YouTube trending search and Reddit scraping
using the existing ingestion infrastructure.

Usage:
    from app.services.web_search import search_web, search_youtube_trends

    results = search_web("personal branding trends 2026", max_results=10)
    yt_results = search_youtube_trends("personal branding", max_results=5)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("app.services.web_search")


# ── Web Search ─────────────────────────────────────────────


def search_web(
    query: str,
    max_results: int = 10,
    search_depth: str = "basic",
) -> List[Dict[str, Any]]:
    """Search the web for real-time information.

    Tries Tavily first (if API key exists), falls back to DuckDuckGo.

    Returns list of:
        {"title": str, "url": str, "snippet": str, "source": "tavily"|"duckduckgo"}
    """
    if not query or not query.strip():
        return []

    # Try Tavily first (better quality, structured for LLMs)
    tavily_key = getattr(settings, "tavily_api_key", "")
    if tavily_key:
        try:
            return _search_tavily(query, max_results, search_depth, tavily_key)
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)

    # Free fallback: DuckDuckGo
    try:
        return _search_duckduckgo(query, max_results)
    except Exception as e:
        logger.error("DuckDuckGo search also failed: %s", e)
        return []


def _search_tavily(
    query: str,
    max_results: int,
    search_depth: str,
    api_key: str,
) -> List[Dict[str, Any]]:
    """Search using Tavily API."""
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=False,
    )

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")[:500],
            "source": "tavily",
            "score": r.get("score", 0),
        })

    logger.info("Tavily search: %d results for '%s'", len(results), query[:50])
    return results


def _search_duckduckgo(
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search using DuckDuckGo (free, no API key)."""
    from ddgs import DDGS

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")[:500],
                "source": "duckduckgo",
            })

    logger.info("DuckDuckGo search: %d results for '%s'", len(results), query[:50])
    return results


# ── YouTube Trend Research ──────────────────────────────────


def search_youtube_trends(
    query: str,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search YouTube for trending/recent content on a topic.

    Uses DuckDuckGo video search scoped to YouTube,
    then pulls metadata for each result.
    """
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.videos(
                f"site:youtube.com {query}",
                max_results=max_results,
            ):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("content", r.get("href", "")),
                    "description": r.get("description", "")[:300],
                    "publisher": r.get("publisher", ""),
                    "views": r.get("statistics", {}).get("viewCount", ""),
                    "duration": r.get("duration", ""),
                    "source": "youtube_search",
                })

        logger.info(
            "YouTube trend search: %d results for '%s'",
            len(results), query[:50],
        )
        return results

    except Exception as e:
        logger.warning("YouTube trend search failed: %s", e)
        return []


# ── Reddit Research ─────────────────────────────────────────


def search_reddit(
    query: str,
    subreddit: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search Reddit for discussions on a topic.

    Uses DuckDuckGo scoped to reddit.com. Returns post titles,
    snippets, and URLs.
    """
    try:
        from ddgs import DDGS

        search_query = f"site:reddit.com {query}"
        if subreddit:
            search_query = f"site:reddit.com/r/{subreddit} {query}"

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(search_query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")[:500],
                    "source": "reddit",
                })

        logger.info(
            "Reddit search: %d results for '%s'",
            len(results), query[:50],
        )
        return results

    except Exception as e:
        logger.warning("Reddit search failed: %s", e)
        return []


# ── LinkedIn Search ────────────────────────────────────────


def search_linkedin(
    query: str,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search LinkedIn for posts and articles on a topic.

    Uses web search scoped to linkedin.com/posts and linkedin.com/pulse.
    """
    search_query = f"site:linkedin.com/posts OR site:linkedin.com/pulse {query}"
    results = search_web(search_query, max_results=max_results)
    for r in results:
        r["source"] = "linkedin"
    return results


# ── TikTok Search ─────────────────────────────────────────


def search_tiktok(
    query: str,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search TikTok for trending content on a topic.

    Uses web search scoped to tiktok.com.
    """
    search_query = f"site:tiktok.com {query}"
    results = search_web(search_query, max_results=max_results)
    for r in results:
        r["source"] = "tiktok"
    return results


# ── Competitor Content Analysis ─────────────────────────────


def analyze_competitor_url(url: str) -> Dict[str, Any]:
    """Fetch and analyze a competitor's content from URL.

    Uses the existing ingestion infrastructure to extract text,
    then returns a summary for research use.
    """
    try:
        from app.services.ingestion import extract_text_from_url

        result = extract_text_from_url(url)
        if result.get("error") and not result.get("text"):
            return {
                "url": url,
                "error": result["error"],
                "text": "",
                "source_type": result.get("source_type", "unknown"),
            }

        return {
            "url": url,
            "text": result["text"][:3000],  # Cap at 3000 chars for prompt
            "source_type": result.get("source_type", "webpage"),
            "metadata": result.get("metadata", {}),
            "error": "",
        }

    except Exception as e:
        logger.warning("Competitor analysis failed for %s: %s", url, e)
        return {"url": url, "error": str(e), "text": "", "source_type": "unknown"}
