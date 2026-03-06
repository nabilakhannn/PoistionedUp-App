"""Video Content Service — Slice 108.

Handles video script generation and optional API integrations:
- Script-only: Jumbo writes the script, user records themselves
- HeyGen: AI avatar talking head (requires HEYGEN_API_KEY)
- Kie AI / Veo3.1: AI-generated faceless video (requires KIE_AI_API_KEY)

Graceful degradation if API keys are not configured.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Optional

import httpx

logger = logging.getLogger("app.services.video_content")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))


# ── Script Generation ────────────────────────────────────────────────


def generate_video_script(
    brand_id: str,
    user_id: str,
    topic: str,
    video_type: str = "talking_head",
    duration_seconds: int = 60,
    platform: str = "linkedin",
) -> dict:
    """Generate a video script using brand context.

    video_type: 'talking_head', 'faceless', 'short_form'
    duration_seconds: target duration (15, 30, 60, 180, 300)
    platform: target platform for optimization
    """
    if not _is_valid_uuid(brand_id) or not _is_valid_uuid(user_id):
        raise ValueError("Invalid brand_id or user_id")

    from app.services.jumbo_pipeline import get_brand_context
    brand_ctx = get_brand_context(brand_id) or {}

    # Build script prompt based on type
    type_instructions = {
        "talking_head": (
            "Write a talking head video script. Include:\n"
            "- Speaker notes and key talking points\n"
            "- Natural speech rhythm, short sentences\n"
            "- Timing marks: [0:00-0:03 HOOK], [0:03-0:15 STORY], etc.\n"
            "- First 2 sentences: NO commas (minimize pauses)\n"
            "- Last sentence: clear CTA\n"
        ),
        "faceless": (
            "Write a faceless narration script with visual cues. Include:\n"
            "- Visual cue markers: [CUT TO B-ROLL], [SHOW TEXT ON SCREEN]\n"
            "- Timing marks for each section\n"
            "- 6th grade reading level for spoken content\n"
            "- Engaging visuals described in brackets\n"
            "- Last sentence: clear CTA\n"
        ),
        "short_form": (
            "Write a short-form viral video script (TikTok/Reels/Shorts). Include:\n"
            "- HOOK in first 2 seconds (pattern interrupt)\n"
            "- Fast pacing, punchy lines\n"
            "- [TEXT ON SCREEN] markers for key phrases\n"
            "- End with CTA or loop trigger\n"
        ),
    }

    duration_label = f"{duration_seconds}s" if duration_seconds < 60 else f"{duration_seconds // 60}min"

    system_prompt = (
        "You are a professional video script writer for personal brands.\n"
        f"Brand context: {brand_ctx}\n\n"
        f"Target platform: {platform}\n"
        f"Target duration: {duration_label}\n\n"
        f"{type_instructions.get(video_type, type_instructions['talking_head'])}\n"
        "Output the script in clean format with timing marks and visual cues.\n"
        "Keep it natural, conversational, and on-brand.\n"
    )

    try:
        from openai import OpenAI
        client = OpenAI(timeout=60.0, max_retries=0)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a {video_type} video script about: {topic}"},
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        script = response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("Script generation failed: %s", exc)
        # Fallback to simple template
        script = (
            f"[0:00-0:03 HOOK]\n"
            f"Here's what most people get wrong about {topic}...\n\n"
            f"[0:03-0:30 STORY]\n"
            f"Let me tell you what I've learned...\n\n"
            f"[0:30-{duration_label} CTA]\n"
            f"Follow for more insights like this.\n"
        )

    # Save as deliverable
    try:
        from app.deps import get_admin_client
        sb = get_admin_client()
        deliverable_id = str(uuid.uuid4())
        sb.table("agent_deliverables").insert({
            "id": deliverable_id,
            "user_id": user_id,
            "deliverable_type": "video_script",
            "content": script,
            "status": "review",
            "source": "campaign",
            "created_by_agent_id": "jumbo",
        }).execute()
    except Exception as exc:
        logger.warning("Failed to save video script deliverable: %s", exc)
        deliverable_id = None

    return {
        "script": script,
        "video_type": video_type,
        "duration_seconds": duration_seconds,
        "platform": platform,
        "deliverable_id": deliverable_id,
    }


# ── HeyGen Integration ──────────────────────────────────────────────


def generate_heygen_video(
    script: str,
    avatar_id: str = "default",
    voice_id: str = "default",
    emotion: str = "friendly",
    speed: float = 1.0,
    dimensions: str = "1080x1920",
) -> dict:
    """Submit a video generation request to HeyGen API.

    Returns: { task_id, status } or error if key not configured.
    """
    api_key = os.environ.get("HEYGEN_API_KEY")
    if not api_key:
        return {"error": "HEYGEN_API_KEY not configured", "available": False}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.heygen.com/v2/video/generate",
                headers={
                    "X-Api-Key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "video_inputs": [{
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id,
                            "avatar_style": "normal",
                        },
                        "voice": {
                            "type": "text",
                            "input_text": script,
                            "voice_id": voice_id,
                            "speed": speed,
                            "emotion": emotion,
                        },
                    }],
                    "dimension": {
                        "width": int(dimensions.split("x")[0]),
                        "height": int(dimensions.split("x")[1]),
                    },
                },
            )
            data = resp.json()
            return {
                "task_id": data.get("data", {}).get("video_id"),
                "status": "processing",
                "available": True,
            }
    except Exception as exc:
        logger.error("HeyGen API error: %s", exc)
        return {"error": str(exc), "available": True}


def poll_heygen_status(task_id: str) -> dict:
    """Poll HeyGen for video generation status."""
    api_key = os.environ.get("HEYGEN_API_KEY")
    if not api_key:
        return {"error": "HEYGEN_API_KEY not configured"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"https://api.heygen.com/v1/video_status.get?video_id={task_id}",
                headers={"X-Api-Key": api_key},
            )
            data = resp.json().get("data", {})
            return {
                "status": data.get("status", "unknown"),
                "video_url": data.get("video_url"),
                "thumbnail_url": data.get("thumbnail_url"),
                "duration": data.get("duration"),
            }
    except Exception as exc:
        logger.error("HeyGen poll error: %s", exc)
        return {"error": str(exc)}


# ── Kie AI / Veo3.1 Integration ─────────────────────────────────────


def generate_veo_video(
    prompt: str,
    aspect_ratio: str = "9:16",
    reference_image_url: Optional[str] = None,
) -> dict:
    """Submit a video generation request to Kie AI (Veo3.1).

    Returns: { task_id, status } or error if key not configured.
    """
    api_key = os.environ.get("KIE_AI_API_KEY")
    if not api_key:
        return {"error": "KIE_AI_API_KEY not configured", "available": False}

    try:
        payload = {
            "prompt": prompt,
            "model": "veo3_fast",
            "aspect_ratio": aspect_ratio,
        }
        if reference_image_url:
            payload["mode"] = "FIRST_AND_LAST_FRAMES_2_VIDEO"
            payload["image_url"] = reference_image_url

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "https://api.kie.ai/api/v1/veo/generate",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = resp.json()
            return {
                "task_id": data.get("task_id") or data.get("id"),
                "status": "processing",
                "available": True,
            }
    except Exception as exc:
        logger.error("Kie AI error: %s", exc)
        return {"error": str(exc), "available": True}


def poll_veo_status(task_id: str) -> dict:
    """Poll Kie AI for video generation status."""
    api_key = os.environ.get("KIE_AI_API_KEY")
    if not api_key:
        return {"error": "KIE_AI_API_KEY not configured"}

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"https://api.kie.ai/api/v1/veo/status/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            data = resp.json()
            return {
                "status": data.get("status", "unknown"),
                "video_url": data.get("video_url") or data.get("output_url"),
                "duration": data.get("duration"),
            }
    except Exception as exc:
        logger.error("Kie AI poll error: %s", exc)
        return {"error": str(exc)}


# ── Availability Check ───────────────────────────────────────────────


def get_video_capabilities() -> dict:
    """Check which video generation services are available."""
    return {
        "script_only": True,
        "heygen": bool(os.environ.get("HEYGEN_API_KEY")),
        "veo": bool(os.environ.get("KIE_AI_API_KEY")),
    }
