"""Research endpoints: real-time web search, YouTube trends, Reddit."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# ── Schemas ──────────────────────────────────────────────────


class ResearchRequest(BaseModel):
    """POST /research request body."""
    topic: str = Field(..., min_length=1, max_length=500)
    sources: Dict[str, bool] = Field(
        default_factory=lambda: {"web": True, "youtube": True, "reddit": True},
        description="Which sources to search: web, youtube, reddit",
    )
    competitor_urls: List[str] = Field(
        default_factory=list,
        description="Optional list of competitor URLs to analyze",
    )
    max_results: int = Field(default=8, ge=1, le=20)


class ResearchResult(BaseModel):
    """A single research result."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""
    description: Optional[str] = None
    publisher: Optional[str] = None
    views: Optional[str] = None


class ResearchResponse(BaseModel):
    """POST /research response."""
    web_results: List[ResearchResult] = Field(default_factory=list)
    youtube_trends: List[ResearchResult] = Field(default_factory=list)
    reddit_discussions: List[ResearchResult] = Field(default_factory=list)
    competitor_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    signal_count: int = 0
    summary: str = ""


class QuickSearchRequest(BaseModel):
    """POST /research/quick request body."""
    query: str = Field(..., min_length=1, max_length=300)
    max_results: int = Field(default=5, ge=1, le=15)


class QuickSearchResponse(BaseModel):
    """POST /research/quick response."""
    results: List[ResearchResult] = Field(default_factory=list)
    source: str = ""


# ── Endpoints ──────────────────────────────────────────────────


@router.post("", response_model=ResearchResponse)
async def run_research(
    body: ResearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Run comprehensive real-time research across multiple sources.

    Searches web, YouTube, and Reddit based on the topic.
    Optionally analyzes competitor URLs.
    """
    try:
        from app.services.research import run_research as _run_research

        results = _run_research(
            topic=body.topic,
            sources=body.sources,
            competitor_urls=body.competitor_urls if body.competitor_urls else None,
            max_web_results=body.max_results,
            max_youtube_results=min(body.max_results, 5),
            max_reddit_results=min(body.max_results, 5),
        )

        # Convert to response format
        web = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source=r.get("source", "web"),
            )
            for r in results.get("web_results", [])
        ]

        youtube = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                description=r.get("description", ""),
                publisher=r.get("publisher", ""),
                views=r.get("views", ""),
                source="youtube",
            )
            for r in results.get("youtube_trends", [])
        ]

        reddit = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source="reddit",
            )
            for r in results.get("reddit_discussions", [])
        ]

        return ResearchResponse(
            web_results=web,
            youtube_trends=youtube,
            reddit_discussions=reddit,
            competitor_analysis=results.get("competitor_analysis", []),
            signal_count=results.get("signal_count", 0),
            summary=results.get("summary", ""),
        )

    except Exception as e:
        logger.error("Research failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Research service error: {str(e)[:200]}",
        )


@router.post("/quick", response_model=QuickSearchResponse)
async def quick_search(
    body: QuickSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Quick web search for a single query. Fastest path to live data."""
    try:
        from app.services.web_search import search_web

        raw = search_web(body.query, max_results=body.max_results)
        results = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source=r.get("source", "web"),
            )
            for r in raw
        ]

        return QuickSearchResponse(
            results=results,
            source=raw[0].get("source", "web") if raw else "none",
        )

    except Exception as e:
        logger.error("Quick search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search error: {str(e)[:200]}",
        )


@router.post("/youtube", response_model=QuickSearchResponse)
async def youtube_search(
    body: QuickSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Search YouTube for trending content on a topic."""
    try:
        from app.services.web_search import search_youtube_trends

        raw = search_youtube_trends(body.query, max_results=body.max_results)
        results = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                description=r.get("description", ""),
                publisher=r.get("publisher", ""),
                views=r.get("views", ""),
                source="youtube",
            )
            for r in raw
        ]

        return QuickSearchResponse(results=results, source="youtube")

    except Exception as e:
        logger.error("YouTube search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube search error: {str(e)[:200]}",
        )


@router.post("/reddit", response_model=QuickSearchResponse)
async def reddit_search(
    body: QuickSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Search Reddit for discussions on a topic."""
    try:
        from app.services.web_search import search_reddit

        raw = search_reddit(body.query, max_results=body.max_results)
        results = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source="reddit",
            )
            for r in raw
        ]

        return QuickSearchResponse(results=results, source="reddit")

    except Exception as e:
        logger.error("Reddit search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Reddit search error: {str(e)[:200]}",
        )


@router.post("/linkedin", response_model=QuickSearchResponse)
async def linkedin_search(
    body: QuickSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Search LinkedIn for posts and articles on a topic."""
    try:
        from app.services.web_search import search_web

        raw = search_web(
            f"site:linkedin.com/posts OR site:linkedin.com/pulse {body.query}",
            max_results=body.max_results,
        )
        results = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source="linkedin",
            )
            for r in raw
        ]

        return QuickSearchResponse(results=results, source="linkedin")

    except Exception as e:
        logger.error("LinkedIn search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn search error: {str(e)[:200]}",
        )


@router.post("/tiktok", response_model=QuickSearchResponse)
async def tiktok_search(
    body: QuickSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Search TikTok for content on a topic."""
    try:
        from app.services.web_search import search_web

        raw = search_web(
            f"site:tiktok.com {body.query}",
            max_results=body.max_results,
        )
        results = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source="tiktok",
            )
            for r in raw
        ]

        return QuickSearchResponse(results=results, source="tiktok")

    except Exception as e:
        logger.error("TikTok search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"TikTok search error: {str(e)[:200]}",
        )


@router.post("/feed", response_model=ResearchResponse)
async def research_feed(
    body: ResearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Multi-platform feed search. Searches all requested platforms and returns unified results.

    Unlike the main /research endpoint, this returns results organized for a feed view
    with per-platform results aggregated together.
    """
    try:
        from app.services.web_search import (
            search_web,
            search_youtube_trends,
            search_reddit,
        )

        web_results = []
        youtube_trends = []
        reddit_discussions = []
        signal_count = 0

        sources = body.sources or {}

        # Reddit
        if sources.get("reddit", False):
            try:
                raw = search_reddit(body.topic, max_results=body.max_results)
                reddit_discussions = raw
                signal_count += len(raw)
            except Exception as e:
                logger.warning("Feed reddit search failed: %s", e)

        # YouTube
        if sources.get("youtube", False):
            try:
                raw = search_youtube_trends(body.topic, max_results=body.max_results)
                youtube_trends = raw
                signal_count += len(raw)
            except Exception as e:
                logger.warning("Feed youtube search failed: %s", e)

        # LinkedIn (via web search scoped to linkedin.com)
        if sources.get("linkedin", False):
            try:
                raw = search_web(
                    f"site:linkedin.com/posts OR site:linkedin.com/pulse {body.topic}",
                    max_results=body.max_results,
                )
                for r in raw:
                    r["source"] = "linkedin"
                web_results.extend(raw)
                signal_count += len(raw)
            except Exception as e:
                logger.warning("Feed linkedin search failed: %s", e)

        # TikTok (via web search scoped to tiktok.com)
        if sources.get("tiktok", False):
            try:
                raw = search_web(
                    f"site:tiktok.com {body.topic}",
                    max_results=body.max_results,
                )
                for r in raw:
                    r["source"] = "tiktok"
                web_results.extend(raw)
                signal_count += len(raw)
            except Exception as e:
                logger.warning("Feed tiktok search failed: %s", e)

        # General web (fallback / "All" tab)
        if sources.get("web", False):
            try:
                raw = search_web(body.topic, max_results=body.max_results)
                web_results.extend(raw)
                signal_count += len(raw)
            except Exception as e:
                logger.warning("Feed web search failed: %s", e)

        # Convert to response format
        web = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source=r.get("source", "web"),
            )
            for r in web_results
        ]

        youtube = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                description=r.get("description", ""),
                publisher=r.get("publisher", ""),
                views=r.get("views", ""),
                source="youtube",
            )
            for r in youtube_trends
        ]

        reddit = [
            ResearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                source="reddit",
            )
            for r in reddit_discussions
        ]

        return ResearchResponse(
            web_results=web,
            youtube_trends=youtube,
            reddit_discussions=reddit,
            competitor_analysis=[],
            signal_count=signal_count,
            summary=f"Found {signal_count} results across selected platforms.",
        )

    except Exception as e:
        logger.error("Research feed failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Feed search error: {str(e)[:200]}",
        )
