"""Client Deliverables service — Slice 98.

Generates professional client-facing deliverables using Claude Sonnet 4.6:
  - generate_proposal()     — full HTML proposal from session + brand profile + intake form
  - generate_landing_page() — responsive HTML landing page from brand profile + website scrape
  - generate_nurture_sequence() — 5-email nurture using emotional journals + Hormozi

All outputs saved to agent_deliverables (type=proposal|landing_page|ad_creative|nurture_sequence).
Each deliverable gets a share_token for public preview.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

import anthropic
import httpx

from app.config import settings
from app.deps import get_admin_client
from app.utils.url_validation import validate_url_for_fetch

logger = logging.getLogger("app.services.client_deliverables")

_WRITING_MODEL = "claude-sonnet-4-6"


# ── 1. Proposal Generator ─────────────────────────────────────────────────


async def generate_proposal(
    session_id: str,
    brand_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Generate a full HTML proposal from an account manager session.

    Reads: session action plan + brand profile + intake form (if linked).
    Returns: {"deliverable_id": "...", "html": "...", "share_token": "..."}
    """
    sb = get_admin_client()

    # Load session
    session_row = (
        sb.table("account_manager_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not session_row.data:
        raise ValueError(f"Session {session_id!r} not found")
    session = session_row.data[0]

    # Load brand profile
    brand_row = (
        sb.table("personal_brands")
        .select("name, description, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found")
    brand_name = brand_row.data[0].get("name", "")
    profile = brand_row.data[0].get("profile_json") or {}

    # Load intake form if linked
    intake_context = ""
    if session.get("intake_form_id"):
        intake_row = (
            sb.table("client_intake_forms")
            .select("*")
            .eq("id", session["intake_form_id"])
            .limit(1)
            .execute()
        )
        if intake_row.data:
            f = intake_row.data[0]
            intake_context = f"""
Client Details from Intake Form:
- Business: {f.get("business_name", "")}
- Industry: {f.get("industry", "")}
- Revenue: {f.get("current_revenue", "not disclosed")}
- Primary offer: {f.get("primary_offer", "")} ({f.get("offer_price", "TBD")})
- Target audience: {f.get("target_audience", "")}
- Biggest frustration: {f.get("biggest_frustration", "")}
- Goals: {f.get("goals", "")}"""

    # Build deliverable actions summary
    actions = session.get("action_plan") or []
    content_items = [a["title"] for a in actions if a.get("category") == "content"]
    deliverable_items = [a["title"] for a in actions if a.get("category") == "deliverable"]

    prompt = f"""Generate a professional HTML proposal for:

CLIENT: {session.get("client_name", brand_name)}
CALL SUMMARY: {session.get("summary", "")}
CONTENT ITEMS DISCUSSED: {", ".join(content_items) or "None"}
DELIVERABLES DISCUSSED: {", ".join(deliverable_items) or "None"}
{intake_context}

AGENCY BRAND PROFILE:
- Positioning: {profile.get("positioning", "")}
- ICA: {profile.get("ica_summary", "")}
- Dream Outcome: {profile.get("hormozi", {}).get("dream_outcome", "")}

Create a complete, professional HTML proposal that:
1. Uses a dark, premium design (background: #0a0a0a, accents: #6366f1 purple)
2. Includes: Executive Summary, Proposed Services (based on actions), Investment, Timeline, Next Steps
3. References specific insights from the call summary
4. Ends with a clear call to action
5. Is fully self-contained (inline CSS, no external dependencies)

Return ONLY the complete HTML document starting with <!DOCTYPE html>."""

    html = _call_claude(prompt, system="You are a professional business proposal writer. Return only valid HTML.")

    return _save_deliverable(
        sb=sb,
        user_id=user_id,
        brand_id=brand_id,
        deliverable_type="proposal",
        content=html,
        metadata={"session_id": session_id, "client_name": session.get("client_name", brand_name)},
    )


async def generate_landing_page(
    brand_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Generate a responsive HTML landing page from brand profile + optional website scrape.

    Returns: {"deliverable_id": "...", "html": "...", "share_token": "..."}
    """
    sb = get_admin_client()

    brand_row = (
        sb.table("personal_brands")
        .select("name, description, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found")
    brand_name = brand_row.data[0].get("name", "")
    profile = brand_row.data[0].get("profile_json") or {}

    # Try to scrape website for brand identity clues
    website_html_snippet = ""
    website_url = (profile.get("research_source") or {}).get("website_url", "")
    if website_url:
        try:
            validate_url_for_fetch(website_url)
            resp = httpx.get(website_url, timeout=10.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            website_html_snippet = resp.text[:3000]
        except Exception as exc:
            logger.info("Website scrape skipped for %s: %s", website_url, exc)

    hormozi = profile.get("hormozi") or {}
    anxiety_list = profile.get("anxiety_list") or []
    benefit_list = profile.get("benefit_list") or []
    pain_journal = profile.get("emotional_pain_journal") or ""

    prompt = f"""Generate a complete, responsive HTML landing page for:

CLIENT: {brand_name}
POSITIONING: {profile.get("positioning", "")}
ICA: {profile.get("ica_summary", "")}

OFFER POSITIONING (Hormozi Value Equation):
- Dream Outcome: {hormozi.get("dream_outcome", "")}
- Perceived Likelihood: {hormozi.get("perceived_likelihood", "")}
- Time to Result: {hormozi.get("time_to_result", "")}
- Effort Required: {hormozi.get("effort_sacrifice", "")}
- Guarantee: {hormozi.get("guarantee", "")}
- Risk Reversals: {json.dumps(hormozi.get("risk_reversals", []))}

TOP 5 CLIENT ANXIETIES (use for FAQ section):
{chr(10).join(f"- {a}" for a in (anxiety_list or [])[:5])}

TOP 5 CLIENT BENEFITS (use for benefits section):
{chr(10).join(f"- {b}" for b in (benefit_list or [])[:5])}

EMOTIONAL PAIN JOURNAL EXCERPT (use for hero copy inspiration):
{pain_journal[:500]}

EXISTING WEBSITE HTML SNIPPET (for brand identity clues — colors, tone):
{website_html_snippet[:1500] or "(not available)"}

Create a complete, professional landing page that:
1. Has a strong hero section that speaks directly to the top anxiety
2. Includes: Hero, Problem Section, Solution/Offer, Benefits (3-5), Social Proof placeholder, FAQ (from anxieties), CTA
3. Uses the brand's visual style if detectable from the website snippet, otherwise use clean modern design
4. Has strong, specific copy — not generic marketing language
5. Is fully self-contained (inline CSS + minimal JS, no external CDN dependencies)
6. Is mobile-responsive

Return ONLY the complete HTML document starting with <!DOCTYPE html>."""

    html = _call_claude(prompt, system="You are an expert landing page copywriter and web designer. Return only valid HTML.")

    return _save_deliverable(
        sb=sb,
        user_id=user_id,
        brand_id=brand_id,
        deliverable_type="landing_page",
        content=html,
        metadata={"brand_name": brand_name},
    )


async def generate_nurture_sequence(
    brand_id: str,
    user_id: str,
    lead_context: str,
) -> Dict[str, Any]:
    """Generate a 5-email nurture sequence using emotional journals + Hormozi framework.

    Returns: {"deliverable_id": "...", "sequence": [...5 emails...], "share_token": "..."}
    """
    sb = get_admin_client()

    brand_row = (
        sb.table("personal_brands")
        .select("name, profile_json")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_row.data:
        raise ValueError(f"Brand {brand_id!r} not found")
    brand_name = brand_row.data[0].get("name", "")
    profile = brand_row.data[0].get("profile_json") or {}

    hormozi = profile.get("hormozi") or {}
    pain_journal = profile.get("emotional_pain_journal") or ""
    win_journal = profile.get("emotional_win_journal") or ""
    anxiety_list = profile.get("anxiety_list") or []

    prompt = f"""Create a 5-email nurture sequence for {brand_name}.

LEAD CONTEXT: {lead_context}

EMOTIONAL PAIN JOURNAL (use for Email 1 — identify the pain they're in):
{pain_journal[:600]}

TOP ANXIETIES (use for Email 2 — address biggest fear):
{chr(10).join(f"- {a}" for a in (anxiety_list or [])[:5])}

EMOTIONAL WIN JOURNAL (use for Email 3 — paint the dream):
{win_journal[:600]}

HORMOZI FRAMEWORK:
- Dream Outcome: {hormozi.get("dream_outcome", "")}
- Risk Reversal / Guarantee: {hormozi.get("guarantee", "")}
- Risk Reversals: {json.dumps(hormozi.get("risk_reversals", []))}

EMAIL SEQUENCE STRUCTURE:
Email 1 (Day 1): Empathy — meet them in the pain. Subject: something that makes them feel seen.
Email 2 (Day 3): Address the biggest fear/objection directly.
Email 3 (Day 5): Paint the dream outcome. Show someone who got the result.
Email 4 (Day 8): De-risk the offer. Use the guarantee / risk reversals.
Email 5 (Day 12): CTA — here's exactly what happens when they say yes.

Return a JSON array of 5 objects:
[
  {{"email_number": 1, "day": 1, "subject": "...", "body": "...", "cta": "..."}},
  ...
]

No preamble. Return ONLY the JSON array."""

    raw = _call_claude(prompt, system="You are a world-class email copywriter. Return only valid JSON.")
    try:
        # Extract JSON array
        arr_start = raw.find("[")
        arr_end = raw.rfind("]")
        sequence = json.loads(raw[arr_start:arr_end + 1]) if arr_start != -1 else []
    except Exception:
        sequence = [{"email_number": i + 1, "day": [1, 3, 5, 8, 12][i], "subject": "", "body": raw if i == 0 else "", "cta": ""} for i in range(5)]

    result = _save_deliverable(
        sb=sb,
        user_id=user_id,
        brand_id=brand_id,
        deliverable_type="nurture_sequence",
        content=json.dumps(sequence),
        metadata={"brand_name": brand_name, "lead_context": lead_context[:200]},
    )
    result["sequence"] = sequence
    return result


# ── List / get deliverables ───────────────────────────────────────────────


def list_deliverables(user_id: str, brand_id: str, deliverable_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all deliverables for a brand, newest first."""
    sb = get_admin_client()
    q = (
        sb.table("agent_deliverables")
        .select("id, deliverable_type, version, client_brand, share_token, created_at, metadata")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
    )
    if deliverable_type:
        q = q.eq("deliverable_type", deliverable_type)
    return q.execute().data or []


def get_deliverable(deliverable_id: str, user_id: str) -> Dict[str, Any]:
    """Get a single deliverable by ID (authenticated)."""
    sb = get_admin_client()
    row = (
        sb.table("agent_deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise ValueError(f"Deliverable {deliverable_id!r} not found")
    return row.data[0]


def get_deliverable_by_token(share_token: str) -> Dict[str, Any]:
    """Get a deliverable by share token (public, no auth)."""
    sb = get_admin_client()
    row = (
        sb.table("agent_deliverables")
        .select("id, deliverable_type, content, metadata, created_at, version")
        .eq("share_token", share_token)
        .limit(1)
        .execute()
    )
    if not row.data:
        raise ValueError(f"Deliverable not found for share token")
    return row.data[0]


# ── Helpers ────────────────────────────────────────────────────────────────


def _call_claude(prompt: str, system: str) -> str:
    """One-shot Claude Sonnet call for deliverable generation."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=_WRITING_MODEL,
        max_tokens=4096,
        temperature=0.7,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


def _save_deliverable(
    *,
    sb: Any,
    user_id: str,
    brand_id: str,
    deliverable_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Save deliverable to agent_deliverables and return id + share_token."""
    # Determine next version
    existing = (
        sb.table("agent_deliverables")
        .select("version")
        .eq("user_id", user_id)
        .eq("brand_id", brand_id)
        .eq("deliverable_type", deliverable_type)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    next_version = (existing.data[0]["version"] + 1) if existing.data else 1

    deliverable_id = str(uuid.uuid4())
    row = {
        "id": deliverable_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "deliverable_type": deliverable_type,
        "content": content,
        "status": "review",
        "version": next_version,
        "client_brand": True,
        "metadata": metadata or {},
    }
    inserted = sb.table("agent_deliverables").insert(row).execute()
    share_token = (inserted.data[0].get("share_token") if inserted.data else None) or ""

    return {
        "deliverable_id": deliverable_id,
        "share_token": share_token,
        "version": next_version,
        "deliverable_type": deliverable_type,
        "content": content,
    }
