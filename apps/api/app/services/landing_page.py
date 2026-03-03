"""Landing Page Generator Service — Slice 93.

Two-phase production-line pipeline (mirrors image_gen.py):

  Phase 1 — Structure (Claude Haiku, near-free):
    Description + optional inspiration URL → locked JSON page blueprint
    (sections, headline directions, tone, color hints).
    Inspiration URL analysis via Perplexity — SSRF-protected, graceful degradation.

  Phase 2 — Generate (Claude Sonnet 4.6):
    Blueprint + brand profile → full self-contained HTML with Tailwind CDN.
    Brand colors injected via inline tailwind.config.

Functions:
    structure_page(description, page_goal, target_audience, brand_id,
                   inspiration_url, user_id) -> dict
        Returns page blueprint JSON. Near-free (Haiku only).

    generate_page(structure, description, brand_id, user_id) -> dict
        Returns {html, title, model_used, id, error}.

    research_tools() -> dict
        Returns comparison table of best free landing page builders.
        Uses Perplexity; falls back to hardcoded list if key not set.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger("app.services.landing_page")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_PAGE_GOALS = {"capture_email", "book_call", "sell_product", "build_awareness", "other"}

# ── Hardcoded fallback tool list ───────────────────────────────────────────

_FALLBACK_TOOLS = [
    {"name": "Carrd", "free_tier": "3 sites, custom domain on paid", "drag_drop": True, "custom_domain": False, "templates": 70, "score": 9},
    {"name": "Framer", "free_tier": "framer.site subdomain, no custom domain", "drag_drop": True, "custom_domain": False, "templates": 100, "score": 8},
    {"name": "Mailchimp Landing Pages", "free_tier": "Unlimited pages, limited analytics", "drag_drop": True, "custom_domain": False, "templates": 30, "score": 7},
    {"name": "Google Sites", "free_tier": "Fully free, Google subdomain", "drag_drop": True, "custom_domain": False, "templates": 15, "score": 6},
    {"name": "Netlify + HTML Drop", "free_tier": "100GB bandwidth/month, custom domain free", "drag_drop": False, "custom_domain": True, "templates": 0, "score": 8},
]

# ── Phase 1: Structure prompt ──────────────────────────────────────────────

_STRUCTURE_SYSTEM = """You are a world-class conversion architect.

Your job: transform a product description into a precise landing page blueprint.

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{
  "title": "Page title (8 words max)",
  "sections": [
    {
      "type": "hero",
      "headline_direction": "One sentence describing the headline angle to use",
      "subheadline_direction": "One sentence describing the sub-headline angle",
      "cta_text": "3-5 word CTA button text"
    },
    {
      "type": "problem",
      "headline_direction": "The pain/frustration headline to write",
      "body_direction": "2-3 bullets of specific problems to address"
    },
    {
      "type": "solution",
      "headline_direction": "The outcome/transformation headline",
      "body_direction": "The mechanism — HOW you solve it, briefly"
    },
    {
      "type": "social_proof",
      "proof_type": "testimonials | stats | logos | case_study",
      "direction": "What kind of proof to show and what outcome to highlight"
    },
    {
      "type": "cta",
      "headline_direction": "Final push headline",
      "cta_text": "3-5 word action button text",
      "urgency": "What urgency or guarantee to offer, if any"
    },
    {
      "type": "faq",
      "questions": ["Top 3-4 objections as questions"]
    }
  ],
  "tone": "professional | conversational | bold | empathetic | urgent",
  "color_hint": "A CSS hex color that fits the brand/product mood (e.g. #2563eb)",
  "estimated_word_count": 800
}

Rules:
- hero, problem, solution, cta are REQUIRED. social_proof and faq optional.
- Sections must appear in the order above.
- headline_direction must be a concrete direction, not a generic label.
- Never use placeholder text like "Insert headline here."
"""


def structure_page(
    description: str,
    page_goal: str,
    target_audience: str,
    brand_id: str,
    inspiration_url: Optional[str],
    user_id: str,
) -> dict:
    """Phase 1: use Claude Haiku to produce a locked page blueprint.

    Optionally fetches inspiration URL via Perplexity to ground the structure.
    Near-free (Haiku only). Returns a blueprint dict.
    """
    from app.config import settings

    safe_desc = description[:1000].strip()
    safe_goal = page_goal if page_goal in VALID_PAGE_GOALS else "other"
    safe_audience = target_audience[:500].strip()

    # Inspiration URL: SSRF-validate then analyze via Perplexity
    inspiration_context = ""
    if inspiration_url:
        inspiration_context = _fetch_inspiration_structure(inspiration_url)

    user_msg = (
        f"Product/Service: {safe_desc}\n"
        f"Page goal: {safe_goal}\n"
        f"Target audience: {safe_audience}\n"
    )
    if inspiration_context:
        user_msg += f"\nInspiration page structure (for reference only — rewrite in our brand):\n{inspiration_context}"

    if not settings.anthropic_api_key:
        return _fallback_structure(safe_desc, safe_goal)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=_STRUCTURE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences (mirrors image_gen.py)
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

        result = json.loads(raw)
        return result
    except Exception as exc:
        logger.warning("Page structuring failed: %s", exc)
        return _fallback_structure(safe_desc, safe_goal, error=str(exc))


def _fallback_structure(description: str, goal: str, error: Optional[str] = None) -> dict:
    return {
        "title": description[:60],
        "sections": [
            {"type": "hero", "headline_direction": f"Compelling headline for {goal}", "subheadline_direction": "Clear value proposition", "cta_text": "Get Started"},
            {"type": "problem", "headline_direction": "Address the main pain point", "body_direction": "3 specific frustrations your audience faces"},
            {"type": "solution", "headline_direction": "Introduce your solution", "body_direction": "How you solve it, specifically"},
            {"type": "cta", "headline_direction": "Final call to action", "cta_text": "Get Started Today", "urgency": ""},
        ],
        "tone": "professional",
        "color_hint": "#2563eb",
        "estimated_word_count": 600,
        "error": error,
    }


def _fetch_inspiration_structure(url: str) -> str:
    """Analyze a landing page URL using Perplexity. Returns empty string on any failure."""
    from app.config import settings

    if not settings.perplexity_api_key:
        return ""

    # SSRF protection
    try:
        from app.utils.url_validation import validate_url_for_fetch
        validate_url_for_fetch(url)
    except Exception as exc:
        logger.warning("Inspiration URL rejected (SSRF check): %s | %s", url, exc)
        return ""

    # Sanitize for query injection
    safe_url = re.sub(r"[<>\"';;&]", "", url)[:500]

    try:
        query = (
            f"Analyze the landing page structure at this URL: {safe_url}\n"
            f"Describe: 1) All page sections (hero, problem, social proof, CTA, FAQ etc.) "
            f"2) The main headline and hook used 3) The CTA text 4) The overall conversion strategy. "
            f"Be specific and concise."
        )
        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 800,
            },
            headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Inspiration URL fetch failed: %s", exc)
        return ""


# ── Phase 2: Generate full HTML ────────────────────────────────────────────

_GENERATE_SYSTEM = """You are an expert landing page developer and copywriter.

You will receive a page blueprint (sections with directions) and brand context.
Generate a COMPLETE, self-contained HTML landing page.

Requirements:
- Include <!DOCTYPE html> and all HTML boilerplate
- Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
- Inject brand color via: <script>tailwind.config = { theme: { extend: { colors: { brand: 'BRAND_COLOR' } } } }</script>
- Responsive and mobile-first (use Tailwind responsive prefixes)
- Each section from the blueprint must be present
- Write REAL, compelling copy — not placeholders
- Use the brand's voice, positioning, and ICP language
- No external images (use SVG icons or CSS gradients instead)
- CTA buttons: use bg-brand class for brand color

Output ONLY the complete HTML file. No markdown. No explanation. Start with <!DOCTYPE html>.
"""


def generate_page(
    structure: dict,
    description: str,
    brand_id: str,
    user_id: str,
) -> dict:
    """Phase 2: generate full self-contained HTML from the page blueprint.

    Fetches brand profile to ground the copy in brand voice + ICP.
    Returns {html, title, model_used, id, error}.
    """
    from app.config import settings

    if not settings.anthropic_api_key:
        return {"html": "", "title": "Untitled", "model_used": None, "id": None, "error": "ANTHROPIC_API_KEY not configured"}

    # Fetch brand profile for voice/ICP grounding
    brand_context = _get_brand_context(brand_id, user_id)
    color_hint = structure.get("color_hint", "#2563eb")
    title = structure.get("title", "Landing Page")

    structure_json = json.dumps(structure, indent=2)[:3000]

    user_msg = (
        f"Page blueprint:\n{structure_json}\n\n"
        f"Brand context:\n{brand_context}\n\n"
        f"Brand color (use as 'brand' in Tailwind config): {color_hint}\n"
        f"Original product description: {description[:500]}\n\n"
        f"Write the complete landing page HTML now."
    )

    system = _GENERATE_SYSTEM.replace("BRAND_COLOR", color_hint)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        html = response.content[0].text.strip()

        # Strip accidental markdown fences
        if html.startswith("```"):
            html = html.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        page_id = _save_to_db(
            user_id=user_id,
            brand_id=brand_id,
            title=title,
            description=description,
            structure=structure,
            html_content=html,
            model_used="claude-sonnet-4-6",
        )

        return {
            "html": html,
            "title": title,
            "model_used": "claude-sonnet-4-6",
            "id": page_id,
            "error": None,
        }
    except Exception as exc:
        logger.error("Page generation failed: %s", exc)
        return {"html": "", "title": title, "model_used": None, "id": None, "error": str(exc)}


def _get_brand_context(brand_id: str, user_id: str) -> str:
    """Fetch brand profile from DB. Returns empty string on failure."""
    if not _UUID_RE.match(brand_id):
        return ""
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        res = (
            sb.table("brands")
            .select("name,positioning,tone_of_voice,target_audience,pain_points,unique_value_proposition")
            .eq("id", brand_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        d = res.data or {}
        parts = []
        if d.get("name"):
            parts.append(f"Brand: {d['name']}")
        if d.get("positioning"):
            parts.append(f"Positioning: {d['positioning']}")
        if d.get("tone_of_voice"):
            parts.append(f"Tone: {d['tone_of_voice']}")
        if d.get("target_audience"):
            parts.append(f"Audience: {d['target_audience']}")
        if d.get("pain_points"):
            parts.append(f"Pain points: {d['pain_points']}")
        if d.get("unique_value_proposition"):
            parts.append(f"UVP: {d['unique_value_proposition']}")
        return "\n".join(parts)
    except Exception as exc:
        logger.warning("Could not fetch brand context: %s", exc)
        return ""


def _save_to_db(
    *,
    user_id: str,
    brand_id: str,
    title: str,
    description: str,
    structure: dict,
    html_content: str,
    model_used: str,
) -> Optional[str]:
    """Persist generated page to DB. Returns row id or None on failure."""
    if not user_id:
        return None
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        res = sb.table("generated_landing_pages").insert({
            "user_id": user_id,
            "brand_id": brand_id or None,
            "title": title,
            "description": description[:1000],
            "structure": structure,
            "html_content": html_content,
            "model_used": model_used,
        }).execute()
        rows = res.data or []
        return rows[0]["id"] if rows else None
    except Exception as exc:
        logger.warning("Failed to save landing page to DB: %s", exc)
        return None


# ── Tool research ──────────────────────────────────────────────────────────


def research_tools() -> dict:
    """Search Perplexity for the best free landing page builders.

    Returns a comparison table. Falls back to hardcoded list if no Perplexity key.
    """
    from app.config import settings

    if not settings.perplexity_api_key:
        logger.info("No PERPLEXITY_API_KEY — returning hardcoded tool list")
        return {"tools": _FALLBACK_TOOLS, "source": "cached"}

    try:
        query = (
            "What are the 5 best FREE landing page builders in 2026? "
            "For each tool include: name, free tier limits, drag-and-drop (yes/no), "
            "custom domain on free plan (yes/no), number of templates, and a score 1-10. "
            "Be specific about free tier limits. Format as a list."
        )
        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1000,
            },
            headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
            timeout=20.0,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

        # Use Gemini to parse the Perplexity response into structured JSON
        tools = _parse_tools_with_gemini(raw)
        if tools:
            return {"tools": tools, "source": "live"}
        return {"tools": _FALLBACK_TOOLS, "source": "cached"}
    except Exception as exc:
        logger.warning("Tool research failed: %s — using fallback", exc)
        return {"tools": _FALLBACK_TOOLS, "source": "cached"}


def _parse_tools_with_gemini(raw_text: str) -> Optional[list]:
    """Use Gemini to parse free-form Perplexity output into structured tool list."""
    from app.config import settings

    if not settings.gemini_api_key:
        return None

    prompt = (
        f"Parse this landing page tool comparison into a JSON array.\n"
        f"Each object must have: name (str), free_tier (str), drag_drop (bool), "
        f"custom_domain (bool), templates (int), score (int 1-10).\n"
        f"Return ONLY the JSON array, no markdown.\n\n"
        f"Text to parse:\n{raw_text[:2000]}"
    )

    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        resp = httpx.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            params={"key": settings.gemini_api_key},
            timeout=15.0,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        return json.loads(text)
    except Exception as exc:
        logger.warning("Gemini tool parse failed: %s", exc)
        return None
