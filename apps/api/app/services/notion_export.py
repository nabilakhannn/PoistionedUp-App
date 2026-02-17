"""Notion export service.

Creates a formatted Notion page from a content pack and returns the page URL.
Uses the Notion API directly via httpx (no SDK dependency needed).
"""

import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("app.services.notion_export")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


def _text_block(text: str, block_type: str = "paragraph") -> Dict:
    """Create a Notion rich text block."""
    # Notion has a 2000-char limit per rich_text element
    chunks = []
    for i in range(0, len(text), 2000):
        chunks.append({"type": "text", "text": {"content": text[i : i + 2000]}})

    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": chunks},
    }


def _heading_block(text: str, level: int = 2) -> Dict:
    """Create a Notion heading block (level 1, 2, or 3)."""
    block_type = f"heading_{level}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def _divider() -> Dict:
    """Create a Notion divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


def _build_notion_blocks(pack: Dict[str, Any]) -> List[Dict]:
    """Convert a content pack into a list of Notion blocks."""
    blocks = []

    # YouTube Long-Form
    yt_long = pack.get("youtube_long", {})
    if yt_long:
        blocks.append(_heading_block("YouTube Long-Form Script", 1))

        if yt_long.get("hook"):
            blocks.append(_heading_block("Hook", 3))
            blocks.append(_text_block(yt_long["hook"]))

        for section in yt_long.get("sections", []):
            ts = section.get("timestamp", "")
            heading = section.get("heading", "")
            blocks.append(_heading_block(f"[{ts}] {heading}", 3))
            blocks.append(_text_block(section.get("script", "")))
            if section.get("broll_suggestion"):
                blocks.append(_text_block(f"B-roll: {section['broll_suggestion']}", "callout"))

        blocks.append(_divider())

    # Title Options
    titles = pack.get("titles", [])
    if titles:
        blocks.append(_heading_block("Title Options", 3))
        for i, t in enumerate(titles, 1):
            blocks.append(_text_block(f"{i}. {t}"))

    # Description
    desc = pack.get("description", "")
    if desc:
        blocks.append(_heading_block("Description", 3))
        blocks.append(_text_block(desc))

    # Tags
    tags = pack.get("tags", [])
    if tags:
        blocks.append(_text_block(f"Tags: {', '.join(tags)}"))

    # YouTube Shorts
    shorts = pack.get("youtube_shorts", [])
    if shorts:
        blocks.append(_heading_block("YouTube Shorts", 1))
        for i, s in enumerate(shorts, 1):
            blocks.append(_heading_block(f"Short #{i}", 3))
            if s.get("hook"):
                blocks.append(_text_block(f"Hook: {s['hook']}"))
            blocks.append(_text_block(s.get("script", "")))
            if s.get("cta"):
                blocks.append(_text_block(f"CTA: {s['cta']}"))
        blocks.append(_divider())

    # LinkedIn Posts
    li_posts = pack.get("linkedin_posts", [])
    if li_posts:
        blocks.append(_heading_block("LinkedIn Posts", 1))
        for i, p in enumerate(li_posts, 1):
            ptype = p.get("post_type", "post").title()
            blocks.append(_heading_block(f"Post #{i} ({ptype})", 3))
            if p.get("hook_line"):
                blocks.append(_text_block(p["hook_line"]))
            blocks.append(_text_block(p.get("body", "")))
            if p.get("cta"):
                blocks.append(_text_block(p["cta"]))
        blocks.append(_divider())

    # Twitter Posts
    tw_posts = pack.get("twitter_posts", [])
    if tw_posts:
        blocks.append(_heading_block("Twitter/X Posts", 1))
        for i, t in enumerate(tw_posts, 1):
            blocks.append(_heading_block(f"Tweet #{i} ({t.get('angle', '')})", 3))
            blocks.append(_text_block(t.get("tweet_text", "")))
        blocks.append(_divider())

    # Twitter Thread
    tw_thread = pack.get("twitter_thread", {})
    if tw_thread and tw_thread.get("hook_tweet"):
        blocks.append(_heading_block("Thread", 3))
        blocks.append(_text_block(f"1/ {tw_thread['hook_tweet']}"))
        for j, tweet in enumerate(tw_thread.get("tweets", []), 2):
            blocks.append(_text_block(f"{j}/ {tweet}"))
        blocks.append(_divider())

    # Short-form Scripts
    sf_scripts = pack.get("short_form_scripts", [])
    if sf_scripts:
        blocks.append(_heading_block("Short-Form Scripts", 1))
        for i, s in enumerate(sf_scripts, 1):
            angle = s.get("angle", "").replace("_", " ").title()
            blocks.append(_heading_block(f"Script #{i} ({angle})", 3))
            if s.get("hook"):
                blocks.append(_text_block(f"Hook: {s['hook']}"))
            blocks.append(_text_block(s.get("script", "")))
            if s.get("punchline"):
                blocks.append(_text_block(f"Punchline: {s['punchline']}"))
            if s.get("cta"):
                blocks.append(_text_block(f"CTA: {s['cta']}"))

    return blocks


async def create_notion_page(
    access_token: str,
    pack: Dict[str, Any],
    goal_text: str = "",
) -> str:
    """Create a Notion page from a content pack and return the page URL.

    Creates the page in the user's workspace root (no parent database required).

    Args:
        access_token: Notion OAuth access token
        pack: The content pack dictionary
        goal_text: The workflow goal text for the page title

    Returns:
        The URL of the created Notion page
    """
    page_title = f"PositionedUp: {goal_text[:80]}" if goal_text else "PositionedUp Content Pack"
    blocks = _build_notion_blocks(pack)

    # Notion API limits to 100 blocks per request
    # We'll send the first 100, then append in batches if needed
    first_batch = blocks[:100]
    remaining = blocks[100:]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    # Search for a workspace-level page to use as parent
    # If the user hasn't shared any pages, we create a top-level page
    async with httpx.AsyncClient() as client:
        # First, try to search for available pages
        search_resp = await client.post(
            f"{NOTION_API_BASE}/search",
            headers=headers,
            json={
                "filter": {"value": "page", "property": "object"},
                "page_size": 1,
            },
        )

        parent = {"type": "page_id", "page_id": ""}

        if search_resp.status_code == 200:
            results = search_resp.json().get("results", [])
            if results:
                # Use the first available page as parent
                parent["page_id"] = results[0]["id"]

        # Create the page
        page_body = {
            "parent": parent if parent["page_id"] else {"type": "workspace", "workspace": True},
            "properties": {
                "title": [{"type": "text", "text": {"content": page_title}}],
            },
            "children": first_batch,
        }

        # If no parent page found, use workspace as parent
        if not parent.get("page_id"):
            page_body["parent"] = {"type": "workspace", "workspace": True}

        resp = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=headers,
            json=page_body,
        )

        if resp.status_code not in (200, 201):
            error_body = resp.json()
            logger.error("Notion page creation failed: %s", error_body)
            raise Exception(
                f"Failed to create Notion page: {error_body.get('message', 'Unknown error')}"
            )

        page_data = resp.json()
        page_id = page_data["id"]
        page_url = page_data.get("url", f"https://www.notion.so/{page_id.replace('-', '')}")

        # Append remaining blocks in batches of 100
        for i in range(0, len(remaining), 100):
            batch = remaining[i : i + 100]
            append_resp = await client.patch(
                f"{NOTION_API_BASE}/blocks/{page_id}/children",
                headers=headers,
                json={"children": batch},
            )
            if append_resp.status_code not in (200, 201):
                logger.warning(
                    "Failed to append block batch %d: %s",
                    i // 100 + 1,
                    append_resp.text[:200],
                )

    logger.info("Created Notion page: %s", page_url)
    return page_url
