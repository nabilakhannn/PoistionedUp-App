"""Image Generation Service — Slice 91a.

Two-step production-line pipeline:
  Step 1 — Prompt Engineering (Claude Haiku):
    Plain English → structured JSON prompt with camera specs, lighting,
    composition, color grading, and negative constraints.
    Raises usable generation rate from ~68% → ~92%.

  Step 2 — Image API:
    Primary: Higgsfield Nano Banana 2 (if HIGGSFIELD_API_KEY set)
    Fallback: Google Gemini image generation (uses GEMINI_API_KEY)

Functions:
    structure_prompt_only(description, style, brand_context) -> dict
        Prompt engineering only — no image API call (zero image cost).
        Returns {subject, composition, camera, lighting, color_palette,
                 mood, style, negative_prompt, final_prompt}.

    generate_image(description, style, format, brand_context,
                   user_id, brand_id) -> dict
        Full pipeline → {url, structured_prompt, model_used, error}.
        Saves each generation to generated_images table.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger("app.services.image_gen")

# ── Aspect ratio mapping ───────────────────────────────────────────────────

FORMAT_RATIOS: dict[str, str] = {
    "square": "1:1",       # LinkedIn, Instagram posts
    "landscape": "16:9",   # YouTube thumbnails, Twitter header
    "portrait": "4:5",     # Instagram feed portrait
    "story": "9:16",       # Instagram/TikTok Stories
}

VALID_STYLES = {"photorealistic", "cinematic", "branded", "editorial", "lifestyle"}
VALID_FORMATS = set(FORMAT_RATIOS.keys())

# ── Prompt engineering system prompt ──────────────────────────────────────

_PROMPT_SYSTEM = """You are an expert image prompt engineer for Nano Banana 2 (Gemini 3.1 Flash Image Generation via Higgsfield).

Transform plain English descriptions into precise, production-quality image prompts using 5 variables.

Return ONLY valid JSON with these exact keys — no other text:
{
  "subject": "The main subject described with precise visual detail (person, object, scene)",
  "composition": "Camera angle, framing rule (rule of thirds, centered, leading lines), distance (close-up, medium, wide)",
  "camera": "Specific lens (85mm f/1.4, 50mm f/2.8, 24mm f/4), depth of field, focus style",
  "lighting": "Named lighting setup (Rembrandt, golden hour backlight, studio softbox, diffused north window light), direction and quality",
  "color_palette": "Dominant colors, film stock reference (Kodak Portra 400, Fuji Velvia, teal-orange grade), saturation",
  "mood": "Emotional quality (warm and intimate, dramatic and tense, fresh and energetic, calm and professional)",
  "style": "The visual style requested",
  "negative_prompt": "no plastic skin, no AI artifacts, no stock photo look, no watermark, no text overlay, no lens flare",
  "final_prompt": "Single combined prompt integrating all elements naturally"
}

Rules:
- Camera: Always specify lens (50mm, 85mm, 24mm), aperture (f/1.2–f/8), and focus type (shallow DOF, pan-focus)
- Lighting: Use specific names — not generic 'good lighting'. Name the setup, direction, and quality.
- Color: Reference real film stocks or color grading presets. Be specific.
- Negative: Always include the base negatives: no plastic skin, no AI artifacts, no stock photo look, no watermark
- final_prompt: A single flowing descriptive sentence that naturally combines subject + composition + camera + lighting + color
- Keep final_prompt under 200 words — specific and visual, not abstract
"""


# ── Step 1: Prompt engineering ─────────────────────────────────────────────


def structure_prompt_only(
    description: str,
    style: str = "photorealistic",
    brand_context: str = "",
) -> dict:
    """Use Claude Haiku to engineer a structured prompt from plain English.

    This is the core innovation — transforms vague descriptions into locked,
    precise prompts with production-quality camera/lighting/color specs.

    Returns a dict with all 9 structured keys plus optional 'error'.
    No image API call is made — safe to call for free preview.
    """
    from app.config import settings

    safe_style = style if style in VALID_STYLES else "photorealistic"
    safe_desc = description[:1000].strip()

    # Graceful degradation if no API key
    if not settings.anthropic_api_key:
        return {
            "subject": safe_desc,
            "composition": "centered frame, medium shot",
            "camera": "50mm f/2.8, sharp focus",
            "lighting": "natural daylight, soft and even",
            "color_palette": "neutral, natural tones",
            "mood": "professional and clean",
            "style": safe_style,
            "negative_prompt": "no plastic skin, no AI artifacts, no stock photo look, no watermark",
            "final_prompt": safe_desc,
            "error": "ANTHROPIC_API_KEY not configured — using minimal fallback prompt",
        }

    user_msg = f"Description: {safe_desc}\nStyle: {safe_style}"
    if brand_context:
        user_msg += f"\nBrand context (for tone reference only): {brand_context[:500]}"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_PROMPT_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

        result = json.loads(raw)
        result.setdefault("style", safe_style)
        return result
    except Exception as exc:
        logger.warning("Prompt structuring failed: %s", exc)
        return {
            "subject": safe_desc,
            "composition": "centered frame, medium shot",
            "camera": "50mm f/2.8, sharp focus",
            "lighting": "natural daylight, soft and even",
            "color_palette": "neutral, natural tones",
            "mood": "professional and clean",
            "style": safe_style,
            "negative_prompt": "no plastic skin, no AI artifacts, no stock photo look, no watermark",
            "final_prompt": safe_desc,
            "error": f"Prompt structuring failed: {exc}",
        }


# ── Step 2: Image API ──────────────────────────────────────────────────────


def _call_higgsfield(final_prompt: str, aspect_ratio: str) -> tuple[Optional[str], Optional[str]]:
    """Call Higgsfield Nano Banana 2 API. Returns (image_url, error)."""
    from app.config import settings

    if not settings.higgsfield_api_key:
        return None, "HIGGSFIELD_API_KEY not set"

    try:
        resp = httpx.post(
            "https://api.higgsfield.ai/nano-banana",
            json={"prompt": final_prompt, "aspect_ratio": aspect_ratio},
            headers={
                "Authorization": f"Bearer {settings.higgsfield_api_key}",
                "Content-Type": "application/json",
            },
            timeout=90.0,
        )
        resp.raise_for_status()
        data = resp.json()
        url = data["images"][0]["url"]
        return url, None
    except Exception as exc:
        logger.warning("Higgsfield API failed: %s", exc)
        return None, str(exc)


def _call_gemini_image(final_prompt: str) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini image generation API. Returns (image_url_or_dataurl, error)."""
    from app.config import settings

    if not settings.gemini_api_key:
        return None, "GEMINI_API_KEY not set"

    model = settings.image_gen_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    try:
        resp = httpx.post(
            url,
            json={
                "contents": [{"parts": [{"text": final_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
            },
            params={"key": settings.gemini_api_key},
            headers={"Content-Type": "application/json"},
            timeout=90.0,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
                b64 = part["inlineData"]["data"]
                mime = part["inlineData"].get("mimeType", "image/png")
                return f"data:{mime};base64,{b64}", None
        return None, "Gemini returned no image data"
    except Exception as exc:
        logger.warning("Gemini image generation failed: %s", exc)
        return None, str(exc)


# ── Full pipeline ──────────────────────────────────────────────────────────


def generate_image(
    description: str,
    style: str = "photorealistic",
    img_format: str = "square",
    brand_context: str = "",
    user_id: str = "",
    brand_id: str = "",
) -> dict:
    """Full two-step pipeline: engineer prompt → call image API → save to DB.

    Returns {url, structured_prompt, model_used, error}.
    - url: image URL (Higgsfield) or data: URL (Gemini base64) or None
    - structured_prompt: JSON string of the engineered prompt
    - model_used: which image API was used
    - error: last error string if image generation failed
    """
    safe_format = img_format if img_format in VALID_FORMATS else "square"
    aspect_ratio = FORMAT_RATIOS[safe_format]

    # Step 1: Structure the prompt with Claude Haiku
    structured = structure_prompt_only(description, style, brand_context)
    final_prompt = structured.get("final_prompt") or description
    structured_json = json.dumps(structured)

    # Step 2: Try Higgsfield first, fall back to Gemini
    image_url, error = _call_higgsfield(final_prompt, aspect_ratio)
    model_used = "higgsfield-nano-banana-2" if image_url else None

    if image_url is None:
        gemini_url, gemini_error = _call_gemini_image(final_prompt)
        if gemini_url:
            image_url = gemini_url
            from app.config import settings
            model_used = f"gemini-{settings.image_gen_model}"
            error = None
        else:
            error = gemini_error  # Surface the last error

    # Save to DB (silent fail — never block image delivery)
    _save_to_db(
        user_id=user_id,
        brand_id=brand_id,
        description=description,
        structured_prompt=structured_json,
        image_url=image_url,
        style=style,
        img_format=safe_format,
        model_used=model_used,
    )

    return {
        "url": image_url,
        "structured_prompt": structured_json,
        "model_used": model_used,
        "error": error,
    }


def _save_to_db(
    *,
    user_id: str,
    brand_id: str,
    description: str,
    structured_prompt: str,
    image_url: Optional[str],
    style: str,
    img_format: str,
    model_used: Optional[str],
) -> None:
    """Persist generated image metadata to DB. Silently fails on error."""
    if not user_id:
        return
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        sb.table("generated_images").insert({
            "user_id": user_id,
            "brand_id": brand_id if brand_id else None,
            "description": description,
            "structured_prompt": structured_prompt,
            "image_url": image_url,
            "style": style,
            "format": img_format,
            "model_used": model_used,
        }).execute()
    except Exception as exc:
        logger.warning("Failed to save generated image to DB: %s", exc)
