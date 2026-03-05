"""Newsletter Router — Slice 95.

Two endpoints:
  GET  /newsletter/draft?brand_id=  — get latest draft from agent_deliverables
  POST /newsletter/generate         — generate newsletter from latest research_brief

Newsletter reuses the agent_deliverables table (content_type='newsletter')
to stay consistent with QA, Ad Creative, and other draft systems.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.services.lead_gen import _claude_sonnet

logger = logging.getLogger("app.routers.newsletter")

router = APIRouter(tags=["newsletter"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ── Schema ─────────────────────────────────────────────────────────────────


class GenerateNewsletterRequest(BaseModel):
    brand_id: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/newsletter/draft")
async def get_newsletter_draft(
    brand_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
) -> Optional[dict]:
    """Return the latest newsletter draft for a brand.

    Returns null (200 with body null) if none exists — frontend shows empty state.
    """
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()
    result = (
        sb.table("agent_deliverables")
        .select("id, content, created_at, updated_at")
        .eq("brand_id", brand_id)
        .eq("user_id", user.id)
        .eq("deliverable_type", "newsletter")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    row = result.data[0]
    return {
        "id": row["id"],
        "content": row.get("content", ""),
        "created_at": str(row.get("created_at", "")),
    }


@router.post("/newsletter/generate")
async def generate_newsletter(
    body: GenerateNewsletterRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Generate a 400-600 word newsletter from the latest research brief.

    Reads latest research_briefs entry → Claude Sonnet writes newsletter in brand voice
    → saves to agent_deliverables (type=newsletter, status=draft) → returns draft.
    """
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    sb = get_admin_client()

    # 1. Fetch latest research brief (IDOR via user_id check on personal_brands)
    brief_result = (
        sb.table("research_briefs")
        .select("content, created_at")
        .eq("brand_id", body.brand_id)
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not brief_result.data:
        raise HTTPException(
            422,
            "No research brief found. Run the pipeline first to generate research, "
            "then come back to generate your newsletter."
        )
    brief = brief_result.data[0]
    brief_content = brief.get("content", "")[:4000]

    # 2. Fetch brand profile for voice
    brand_result = (
        sb.table("personal_brands")
        .select("name, profile_json")
        .eq("id", body.brand_id)
        .eq("user_id", user.id)
        .limit(1)
        .execute()
    )
    brand_name = "Your Brand"
    brand_voice = ""
    brand_audience = ""
    if brand_result.data:
        row = brand_result.data[0]
        brand_name = row.get("name", "Your Brand")
        profile = row.get("profile_json") or {}
        messaging = profile.get("messaging") or {}
        ica = profile.get("ica") or {}
        brand_voice = messaging.get("tone", "professional, warm, value-driven")
        brand_audience = ica.get("target_market", "your audience")

    # 3. Generate newsletter with Claude Sonnet
    prompt = f"""You are writing a weekly email newsletter for "{brand_name}".

AUDIENCE: {brand_audience}
VOICE/TONE: {brand_voice}

RESEARCH BRIEF (what happened in your industry this week):
{brief_content}

TASK: Write a 400-600 word newsletter email based on the research above.

Structure:
- Subject line: compelling, specific to the research topic (not generic)
- Opening hook: 1 sentence that pulls the reader in
- Main insight: 2-3 paragraphs explaining the key finding and why it matters to your audience
- Practical takeaway: 1 actionable thing they can do this week
- Closing: warm sign-off that feels personal

Write in first person, conversational tone. No fluff. No excessive emojis.
Use short paragraphs (2-3 sentences max).

Start with "Subject: ..." on the first line, then blank line, then the body.
"""

    newsletter_text = _claude_sonnet(prompt, max_tokens=1000)

    if not newsletter_text or newsletter_text.startswith("{"):
        raise HTTPException(500, "Newsletter generation failed — please try again")

    # 4. Save to agent_deliverables (reuse existing pattern)
    # Check if agent_deliverables has a content_type or deliverable_type column
    save_row = {
        "user_id": user.id,
        "brand_id": body.brand_id,
        "content": newsletter_text,
        "deliverable_type": "newsletter",
        "status": "draft",
    }

    try:
        save_result = sb.table("agent_deliverables").insert(save_row).execute()
        if save_result.data:
            saved = save_result.data[0]
            return {
                "id": saved["id"],
                "content": newsletter_text,
                "created_at": str(saved.get("created_at", "")),
            }
    except Exception as exc:
        logger.warning("Failed to save newsletter to agent_deliverables: %s", exc)
        # Return without saving — user can still copy from the response
        return {
            "id": None,
            "content": newsletter_text,
            "created_at": "",
        }

    return {
        "id": None,
        "content": newsletter_text,
        "created_at": "",
    }
