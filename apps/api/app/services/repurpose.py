"""Content Repurposing Service.

Takes a single piece of content and generates platform-specific versions
for multiple target platforms using LLM-powered adaptation.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import Any, Dict, List, Optional

from supabase import Client

from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response
from worker.graph.prompts import repurpose as prompts

logger = logging.getLogger(__name__)


def _get_brand_context(user_id: str, brand_id: Optional[str], sb: Client) -> Dict[str, Any]:
    """Fetch brand profile for prompt context."""
    if not brand_id:
        return {}
    try:
        resp = (
            sb.table("personal_brands")
            .select("profile_json")
            .eq("id", brand_id)
            .eq("user_id", user_id)
            .execute()
        )
        if resp.data:
            return resp.data[0].get("profile_json", {})
    except Exception as e:
        logger.debug("Brand context unavailable: %s", e)
    return {}


def _format_brand_context(profile: Dict[str, Any]) -> str:
    """Extract brand positioning for prompt injection."""
    brand = profile.get("brand", {})
    if not brand:
        return "No brand positioning defined yet."

    parts = []
    if brand.get("statement"):
        parts.append(f"Brand statement: {brand['statement']}")
    it = brand.get("it_factor", {})
    if it.get("unfair_advantage"):
        parts.append(f"IT factor: {it['unfair_advantage']}")
    if brand.get("content_pillars"):
        parts.append(f"Content pillars: {', '.join(brand['content_pillars'])}")
    return "\n".join(parts) if parts else "No brand positioning defined yet."


def _fetch_source_content(source_id: str, user_id: str, sb: Client) -> Optional[str]:
    """Fetch source content from scheduled_items or content_assets by ID."""
    # Try scheduled_items first
    resp = (
        sb.table("scheduled_items")
        .select("title, body_preview, content_json")
        .eq("id", source_id)
        .eq("user_id", user_id)
        .execute()
    )
    if resp.data:
        item = resp.data[0]
        cj = item.get("content_json", {})
        body = cj.get("body", "") or item.get("body_preview", "")
        title = item.get("title", "")
        return f"{title}\n\n{body}" if body else title

    # Try content_assets
    resp = (
        sb.table("content_assets")
        .select("type, content_json")
        .eq("id", source_id)
        .execute()
    )
    if resp.data:
        asset = resp.data[0]
        cj = asset.get("content_json", {})
        # Extract text from various asset types
        if isinstance(cj, dict):
            parts = []
            for key in ("body", "script", "tweet_text", "hook_line", "hook", "title"):
                if cj.get(key):
                    parts.append(str(cj[key]))
            if cj.get("sections"):
                for section in cj["sections"]:
                    if isinstance(section, dict):
                        if section.get("heading"):
                            parts.append(section["heading"])
                        if section.get("content"):
                            parts.append(section["content"])
            return "\n\n".join(parts) if parts else json.dumps(cj)
        return str(cj)

    return None


def repurpose_content(
    user_id: str,
    source_text: str,
    source_platform: str,
    target_platforms: List[str],
    brand_id: Optional[str],
    sb: Client,
) -> List[Dict[str, Any]]:
    """Repurpose source content into multiple platform-specific versions.

    Args:
        user_id: The user's ID.
        source_text: The source content text.
        source_platform: Platform the source was created for.
        target_platforms: List of platforms to repurpose into.
        brand_id: Optional brand ID for voice context.
        sb: Supabase client.

    Returns:
        List of repurposed items with platform, content_type, title, body, metadata.
    """
    profile = _get_brand_context(user_id, brand_id, sb)
    brand_context = _format_brand_context(profile)
    voice = json.dumps(profile.get("brand_voice", {}))

    llm = get_llm_client()

    # ── Parallel repurposing (one thread per target platform) ─────────────
    # Each platform is independent — no data dependencies between them.
    def _repurpose_platform(target: str) -> Dict[str, Any]:
        constraint = prompts.PLATFORM_CONSTRAINTS.get(target)
        if not constraint:
            logger.warning("No constraints defined for platform: %s", target)
            return {
                "platform": target,
                "content_type": "post",
                "title": f"Unsupported platform: {target}",
                "body": "",
                "metadata": {"error": f"No platform constraints for {target}"},
            }
        try:
            user_prompt = prompts.USER.format(
                source_platform=source_platform,
                source_content=source_text[:10000],
                target_platform=target,
                platform_rules=constraint["rules"],
                voice=voice,
                brand_context=brand_context,
                content_type=constraint["content_type"],
            )
            resp = llm.chat(
                messages=[
                    {"role": "system", "content": prompts.SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                model=get_model_for_step("script_generation"),
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            parsed = parse_json_response(resp["content"])
            return {
                "platform": parsed.get("platform", target),
                "content_type": parsed.get("content_type", constraint["content_type"]),
                "title": parsed.get("title", f"Repurposed for {target}"),
                "body": parsed.get("body", ""),
                "metadata": parsed.get("metadata", {}),
            }
        except Exception as e:
            logger.error("Failed to repurpose for %s: %s", target, e)
            return {
                "platform": target,
                "content_type": constraint.get("content_type", "post"),
                "title": f"Repurpose failed for {target}",
                "body": "",
                "metadata": {"error": str(e)},
            }

    max_workers = min(len(target_platforms), 5)
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_repurpose_platform, t): t for t in target_platforms}
        # Collect results preserving original platform order
        platform_results: Dict[str, Dict[str, Any]] = {}
        for future in as_completed(futures):
            result = future.result()
            platform_results[result["platform"]] = result
    # Re-order to match input order
    for target in target_platforms:
        if target in platform_results:
            results.append(platform_results[target])

    logger.info(
        "Repurposed content from %s → %d platforms (%d successful)",
        source_platform,
        len(target_platforms),
        sum(1 for r in results if r["body"]),
    )

    return results
