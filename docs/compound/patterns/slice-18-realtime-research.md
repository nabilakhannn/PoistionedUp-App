# Pattern: Real-Time Research Engine

**Slice:** 18
**Date:** 2026-02-16

## Problem

The AI coaching chat and the content pipeline relied entirely on LLM memory for market knowledge. The signal_research node explicitly said "Future: add real API calls to YouTube, Reddit, etc." No live data was being fetched.

## Solution

Three-layer research stack:

1. **Web search service** (`web_search.py`) with two backends:
   - DuckDuckGo (free, no API key, zero config)
   - Tavily (optional upgrade, cleaner LLM-friendly results)

2. **Research aggregator** (`research.py`) that combines web, YouTube, and Reddit into:
   - Formatted prompt context for LLM injection
   - Structured signal dicts for pipeline use

3. **Context injection** into existing systems:
   - Brand chat: `_fetch_research_context()` builds topic from user message + profile, searches live, injects into system prompt
   - Pipeline: `signal_research` node fetches live data before calling LLM

## Key decisions

- **Free-first, upgrade-optional.** DuckDuckGo works with zero config. Tavily is better but costs money. System tries Tavily first (if key exists), falls back to DDG.
- **Context injection, not separate step.** Research data goes into the existing system prompt as a context block. The AI sees it alongside the conversation and decides when to reference it. No separate "research step" in the UX.
- **Graceful degradation everywhere.** Every search call is wrapped in try/except. If web search fails, YouTube fails, Reddit fails, the system continues without it. No crash, no error to the user.
- **Max chars cap.** `format_research_for_prompt()` takes a `max_chars` param (default 4000) to avoid blowing up the context window.

## Pattern: tiered search with graceful fallback

```python
def search_web(query, max_results=10):
    # Try premium first
    if settings.tavily_api_key:
        try:
            return _search_tavily(query, max_results)
        except Exception:
            pass  # Fall through to free

    # Free fallback
    try:
        return _search_duckduckgo(query, max_results)
    except Exception:
        return []  # Silent failure
```

## Pattern: research context injection

```python
def build_chat_messages(module, conversation, ..., research_context=""):
    system = MODULE_SYSTEMS[module] + HUMAN_WRITING_RULES

    if research_context:
        system += research_context + (
            "\nWhen relevant, weave in specific data points. "
            "Don't dump all research at once. Use it naturally."
        )
```

## Reuse

Apply this tiered-fallback pattern whenever adding external API dependencies. Always have a free path and a premium path with graceful degradation between them.
