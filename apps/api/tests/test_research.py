"""Tests for real-time research services and endpoints."""

from __future__ import annotations

import pytest


# ── Unit tests: web_search service ──────────────────────────


class TestSearchWeb:
    """Test the web search service."""

    def test_search_web_returns_results(self):
        """DuckDuckGo search should return results with title, url, snippet."""
        from app.services.web_search import search_web

        results = search_web("python programming", max_results=3)
        assert isinstance(results, list)
        # DuckDuckGo might rate-limit, but should try
        if results:
            r = results[0]
            assert "title" in r
            assert "url" in r
            assert "snippet" in r
            assert r["source"] in ("duckduckgo", "tavily")

    def test_search_web_empty_query_returns_empty(self):
        """Empty query should return empty list, not error."""
        from app.services.web_search import search_web

        results = search_web("", max_results=3)
        assert results == []

    def test_search_web_whitespace_query_returns_empty(self):
        """Whitespace-only query should return empty list."""
        from app.services.web_search import search_web

        results = search_web("   ", max_results=3)
        assert results == []

    def test_search_reddit_returns_results(self):
        """Reddit search should return results."""
        from app.services.web_search import search_reddit

        results = search_reddit("personal branding", max_results=3)
        assert isinstance(results, list)
        if results:
            r = results[0]
            assert "title" in r
            assert r["source"] == "reddit"


# ── Unit tests: research aggregator ─────────────────────────


class TestResearchAggregator:
    """Test the research aggregator."""

    def test_run_research_returns_structure(self):
        """Research should return expected dict structure."""
        from app.services.research import run_research

        result = run_research(
            topic="content marketing",
            sources={"web": True, "youtube": False, "reddit": False},
            max_web_results=2,
        )
        assert "web_results" in result
        assert "youtube_trends" in result
        assert "reddit_discussions" in result
        assert "signal_count" in result
        assert "summary" in result
        assert isinstance(result["signal_count"], int)

    def test_format_research_for_prompt(self):
        """Formatted research should be a non-empty string."""
        from app.services.research import run_research, format_research_for_prompt

        result = run_research(
            topic="business coaching",
            sources={"web": True, "youtube": False, "reddit": False},
            max_web_results=2,
        )
        formatted = format_research_for_prompt(result, max_chars=1000)

        if result["signal_count"] > 0:
            assert len(formatted) > 0
            assert "REAL-TIME RESEARCH DATA" in formatted

    def test_format_research_as_signals(self):
        """Signals should be list of dicts with expected keys."""
        from app.services.research import run_research, format_research_as_signals

        result = run_research(
            topic="coaching tips",
            sources={"web": True, "youtube": False, "reddit": False},
            max_web_results=2,
        )
        signals = format_research_as_signals(result)

        if signals:
            s = signals[0]
            assert "type" in s
            assert "title" in s
            assert "description" in s
            assert "source" in s
            assert s.get("live_data") is True

    def test_format_research_truncates(self):
        """Should truncate to max_chars."""
        from app.services.research import format_research_for_prompt

        # Fake large result
        fake_research = {
            "web_results": [
                {"title": f"Article {i}", "url": f"https://example.com/{i}", "snippet": "A" * 500}
                for i in range(20)
            ],
            "youtube_trends": [],
            "reddit_discussions": [],
            "competitor_analysis": [],
        }
        formatted = format_research_for_prompt(fake_research, max_chars=500)
        assert len(formatted) <= 600  # Some buffer for truncation message


# ── Integration tests: research API endpoints ────────────────


class TestResearchEndpoints:
    """Test the /research API endpoints via TestClient."""

    @pytest.fixture
    def client(self):
        """Create a test client with auth dependency overridden."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import CurrentUser, get_current_user

        mock_user = CurrentUser(id="test-user-id", email="test@example.com")
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_research_endpoint_exists(self, client):
        """POST /research should return 200 or 502 (if search fails), not 404."""
        resp = client.post("/research", json={
            "topic": "personal branding",
            "sources": {"web": True, "youtube": False, "reddit": False},
            "max_results": 2,
        })
        assert resp.status_code in (200, 502)

    def test_quick_search_endpoint_exists(self, client):
        """POST /research/quick should not return 404."""
        resp = client.post("/research/quick", json={
            "query": "test query",
            "max_results": 2,
        })
        assert resp.status_code in (200, 502)

    def test_youtube_endpoint_exists(self, client):
        """POST /research/youtube should not return 404."""
        resp = client.post("/research/youtube", json={
            "query": "test query",
            "max_results": 2,
        })
        assert resp.status_code in (200, 502)

    def test_reddit_endpoint_exists(self, client):
        """POST /research/reddit should not return 404."""
        resp = client.post("/research/reddit", json={
            "query": "test query",
            "max_results": 2,
        })
        assert resp.status_code in (200, 502)

    def test_research_requires_topic(self, client):
        """POST /research without topic should return 422."""
        resp = client.post("/research", json={
            "sources": {"web": True},
        })
        assert resp.status_code == 422
