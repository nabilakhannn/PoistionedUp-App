"""Story Extractor — Slice 109.

AI-powered extraction of structured stories from raw user material.
Uses gpt-4o-mini to parse raw_content from experience_journal entries
into structured story objects for prompt injection.

Each extracted story contains:
  - summary: One-sentence summary
  - theme: The core theme (transformation, struggle, insight, etc.)
  - emotion: Dominant emotion
  - key_quote: The most quotable line from the raw text
  - usable_hook: A ready-to-use hook derived from the story
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("app.services.story_extractor")

_EXTRACTION_PROMPT = """You are a story extraction AI. Given raw text (a transcript, note, idea, opinion, or experience), extract ALL distinct stories, insights, or usable content pieces.

For each story/insight found, return a JSON object with:
- "summary": One clear sentence summarizing the story/insight
- "theme": The core theme (e.g., "transformation", "struggle", "breakthrough", "client win", "lesson learned", "contrarian take", "personal experience")
- "emotion": The dominant emotion (e.g., "determination", "frustration", "pride", "vulnerability", "excitement")
- "key_quote": The most quotable/powerful line from the text (exact words if possible)
- "usable_hook": A ready-to-use opening hook for social media derived from this story

Return a JSON array of objects. If the text has no extractable stories, return [].

IMPORTANT:
- Extract EVERY distinct story, not just the main one
- key_quote should use the person's actual words when possible
- usable_hook should be attention-grabbing and under 15 words
- Be generous — even a brief opinion can be a "contrarian take" story

Raw text to extract from:
{raw_text}"""


async def extract_stories(raw_text: str) -> List[Dict[str, Any]]:
    """Extract structured stories from raw text using gpt-4o-mini.

    Returns a list of story objects. Returns empty list on failure.
    Cost: ~$0.0005 per extraction (gpt-4o-mini).
    """
    if not raw_text or not raw_text.strip():
        return []

    # Truncate very long texts to avoid token limits
    text = raw_text[:8000]

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(30.0, connect=5.0),
            max_retries=0,
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract stories from raw text. Always respond with valid JSON arrays."},
                {"role": "user", "content": _EXTRACTION_PROMPT.format(raw_text=text)},
            ],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)

        # Handle both {"stories": [...]} and direct [...] formats
        if isinstance(parsed, list):
            stories = parsed
        elif isinstance(parsed, dict):
            stories = parsed.get("stories", parsed.get("results", []))
        else:
            stories = []

        # Validate each story has required fields
        valid_stories = []
        required_fields = {"summary", "theme", "emotion", "key_quote", "usable_hook"}
        for story in stories:
            if isinstance(story, dict) and required_fields.issubset(story.keys()):
                valid_stories.append({
                    "summary": str(story["summary"])[:500],
                    "theme": str(story["theme"])[:100],
                    "emotion": str(story["emotion"])[:100],
                    "key_quote": str(story["key_quote"])[:500],
                    "usable_hook": str(story["usable_hook"])[:200],
                })

        logger.info("Extracted %d stories from %d chars of text", len(valid_stories), len(text))
        return valid_stories

    except Exception as exc:
        logger.warning("Story extraction failed: %s", str(exc)[:200])
        return []


async def extract_and_save(entry_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Extract stories from a journal entry and save to the extracted_stories column.

    Returns the extracted stories list. Returns empty list on failure.
    """
    from app.deps import get_admin_client
    sb = get_admin_client()

    # Fetch the entry (with IDOR guard)
    result = (
        sb.table("experience_journal")
        .select("id, raw_content")
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("Entry not found or not owned: id=%s user=%s", entry_id, user_id)
        return []

    raw_content = result.data[0].get("raw_content", "")
    stories = await extract_stories(raw_content)

    # Derive tags from extracted story themes + emotions
    tags = list({s.get("theme", "") for s in stories if s.get("theme")} |
                {s.get("emotion", "") for s in stories if s.get("emotion")})

    # Save extracted stories + tags back to the entry
    sb.table("experience_journal").update({
        "extracted_stories": stories,
        "story_tags": tags[:20],  # Cap at 20 tags
    }).eq("id", entry_id).eq("user_id", user_id).execute()

    logger.info("Saved %d extracted stories to entry=%s", len(stories), entry_id)
    return stories


def search_stories_by_theme(
    user_id: str,
    brand_id: str,
    topic: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Search extracted stories by theme relevance.

    Returns the top N stories across all journal entries that match the topic.
    Uses simple text matching on theme and summary fields.
    """
    from app.deps import get_admin_client
    sb = get_admin_client()

    # Fetch all entries with extracted stories for this brand
    result = (
        sb.table("experience_journal")
        .select("id, source_type, extracted_stories, raw_content")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not result.data:
        return []

    # Flatten all stories and score by relevance
    all_stories = []
    topic_lower = topic.lower() if topic else ""

    for entry in result.data:
        stories = entry.get("extracted_stories") or []
        for story in stories:
            if not isinstance(story, dict):
                continue
            # Simple relevance scoring
            score = 0
            summary = str(story.get("summary", "")).lower()
            theme = str(story.get("theme", "")).lower()
            hook = str(story.get("usable_hook", "")).lower()

            if topic_lower:
                if topic_lower in theme:
                    score += 3
                if topic_lower in summary:
                    score += 2
                if topic_lower in hook:
                    score += 1
            else:
                score = 1  # No topic = return any stories

            if score > 0:
                all_stories.append({
                    **story,
                    "_score": score,
                    "_entry_id": entry["id"],
                    "_source_type": entry.get("source_type", "note"),
                })

    # Sort by score descending, return top N
    all_stories.sort(key=lambda s: s["_score"], reverse=True)
    return all_stories[:limit]
