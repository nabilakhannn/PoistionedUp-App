"""Google Docs export service.

Creates a formatted Google Doc from a content pack and returns the doc URL.
Uses the Google Docs API via service account or user OAuth credentials.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("app.services.google_docs")


def _build_doc_requests(pack: Dict[str, Any], goal_text: str = "") -> List[Dict]:
    """Build a list of Google Docs API batchUpdate requests from a content pack.

    Google Docs API uses insertText requests with an index cursor.
    We build the document bottom-up (insert at index 1 each time)
    so the final document reads top-to-bottom.

    Actually, it's easier to build the text first, then format.
    """
    # Build the full text and track formatting ranges
    sections = []

    # Title
    title = f"Content Pack: {goal_text}" if goal_text else "Content Pack"
    sections.append({"text": title + "\n\n", "style": "HEADING_1"})

    # YouTube Long-Form
    yt_long = pack.get("youtube_long", {})
    if yt_long:
        sections.append({"text": "YouTube Long-Form Script\n", "style": "HEADING_2"})

        if yt_long.get("hook"):
            sections.append({"text": "Hook\n", "style": "HEADING_3"})
            sections.append({"text": yt_long["hook"] + "\n\n", "style": "NORMAL"})

        for section in yt_long.get("sections", []):
            ts = section.get("timestamp", "")
            heading = section.get("heading", "")
            sections.append({"text": f"[{ts}] {heading}\n", "style": "HEADING_3"})
            sections.append({"text": section.get("script", "") + "\n\n", "style": "NORMAL"})

    # Titles
    titles = pack.get("titles", [])
    if titles:
        sections.append({"text": "Title Options\n", "style": "HEADING_3"})
        for i, t in enumerate(titles, 1):
            sections.append({"text": f"{i}. {t}\n", "style": "NORMAL"})
        sections.append({"text": "\n", "style": "NORMAL"})

    # Description
    desc = pack.get("description", "")
    if desc:
        sections.append({"text": "Description\n", "style": "HEADING_3"})
        sections.append({"text": desc + "\n\n", "style": "NORMAL"})

    # Tags
    tags = pack.get("tags", [])
    if tags:
        sections.append({"text": f"Tags: {', '.join(tags)}\n\n", "style": "NORMAL"})

    # YouTube Shorts
    shorts = pack.get("youtube_shorts", [])
    if shorts:
        sections.append({"text": "YouTube Shorts\n", "style": "HEADING_2"})
        for i, s in enumerate(shorts, 1):
            sections.append({"text": f"Short #{i}\n", "style": "HEADING_3"})
            sections.append({"text": f"Hook: {s.get('hook', '')}\n\n", "style": "NORMAL"})
            sections.append({"text": s.get("script", "") + "\n", "style": "NORMAL"})
            if s.get("cta"):
                sections.append({"text": f"CTA: {s['cta']}\n\n", "style": "NORMAL"})

    # LinkedIn Posts
    li_posts = pack.get("linkedin_posts", [])
    if li_posts:
        sections.append({"text": "LinkedIn Posts\n", "style": "HEADING_2"})
        for i, p in enumerate(li_posts, 1):
            ptype = p.get("post_type", "post").title()
            sections.append({"text": f"Post #{i} ({ptype})\n", "style": "HEADING_3"})
            if p.get("hook_line"):
                sections.append({"text": p["hook_line"] + "\n\n", "style": "NORMAL"})
            sections.append({"text": p.get("body", "") + "\n", "style": "NORMAL"})
            if p.get("cta"):
                sections.append({"text": p["cta"] + "\n\n", "style": "NORMAL"})

    # Twitter Posts
    tw_posts = pack.get("twitter_posts", [])
    if tw_posts:
        sections.append({"text": "Twitter/X Posts\n", "style": "HEADING_2"})
        for i, t in enumerate(tw_posts, 1):
            sections.append({"text": f"Tweet #{i} ({t.get('angle', '')})\n", "style": "HEADING_3"})
            sections.append({"text": t.get("tweet_text", "") + "\n\n", "style": "NORMAL"})

    # Twitter Thread
    tw_thread = pack.get("twitter_thread", {})
    if tw_thread and tw_thread.get("hook_tweet"):
        sections.append({"text": "Thread\n", "style": "HEADING_3"})
        sections.append({"text": f"1/ {tw_thread['hook_tweet']}\n", "style": "NORMAL"})
        for j, tweet in enumerate(tw_thread.get("tweets", []), 2):
            sections.append({"text": f"{j}/ {tweet}\n", "style": "NORMAL"})
        sections.append({"text": "\n", "style": "NORMAL"})

    # Short-form Scripts
    sf_scripts = pack.get("short_form_scripts", [])
    if sf_scripts:
        sections.append({"text": "Short-Form Scripts (TikTok/Reels/Shorts)\n", "style": "HEADING_2"})
        for i, s in enumerate(sf_scripts, 1):
            angle = s.get("angle", "").replace("_", " ").title()
            sections.append({"text": f"Script #{i} ({angle})\n", "style": "HEADING_3"})
            sections.append({"text": f"Hook: {s.get('hook', '')}\n\n", "style": "NORMAL"})
            sections.append({"text": s.get("script", "") + "\n", "style": "NORMAL"})
            if s.get("punchline"):
                sections.append({"text": f"Punchline: {s['punchline']}\n", "style": "NORMAL"})
            if s.get("cta"):
                sections.append({"text": f"CTA: {s['cta']}\n\n", "style": "NORMAL"})

    return sections


def create_google_doc(credentials, pack: Dict[str, Any], goal_text: str = "") -> str:
    """Create a Google Doc from a content pack and return the document URL.

    Args:
        credentials: google.oauth2.credentials.Credentials
        pack: The content pack dictionary
        goal_text: The workflow goal text for the doc title

    Returns:
        The URL of the created Google Doc
    """
    from googleapiclient.discovery import build

    docs_service = build("docs", "v1", credentials=credentials)
    drive_service = build("drive", "v3", credentials=credentials)

    # Create a blank document
    doc_title = f"PositionedUp: {goal_text[:80]}" if goal_text else "PositionedUp Content Pack"
    doc = docs_service.documents().create(body={"title": doc_title}).execute()
    doc_id = doc["documentId"]

    # Build content sections
    sections = _build_doc_requests(pack, goal_text)

    if not sections:
        logger.warning("Empty content pack, returning empty doc")
        return f"https://docs.google.com/document/d/{doc_id}/edit"

    # Build insertText and updateParagraphStyle requests
    # Insert text first (all at once), then apply styles
    full_text = "".join(s["text"] for s in sections)

    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": full_text,
            }
        }
    ]

    # Calculate ranges for paragraph styles
    cursor = 1
    style_requests = []
    for section in sections:
        text_len = len(section["text"])
        if text_len == 0:
            continue

        style_name = section["style"]
        if style_name != "NORMAL":
            style_requests.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": cursor,
                        "endIndex": cursor + text_len,
                    },
                    "paragraphStyle": {
                        "namedStyleType": style_name,
                    },
                    "fields": "namedStyleType",
                }
            })

        cursor += text_len

    requests.extend(style_requests)

    # Apply all updates in one batch
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("Created Google Doc: %s", doc_url)
    return doc_url
