"""Node 6: Editor — refine content for voice, clarity, and engagement.

Handles all platform content: YouTube, LinkedIn, Twitter, Short-form.
Applies platform-specific constraints (char limits, tone norms).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response, set_tracking_context, safe_node
from worker.graph.prompts import editor as prompts

logger = logging.getLogger("worker.graph.nodes.editor")


@safe_node
def editor(state: Dict[str, Any]) -> Dict[str, Any]:
    """Edit the content pack for voice consistency and clarity across all platforms."""
    _tier = state.get("settings", {}).get("model_tier", "")
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "editor", _tier)

    content_pack = state.get("content_pack", {})
    profile = state.get("profile_snapshot", {})
    settings = state.get("settings", {})
    platforms = settings.get("platforms", ["youtube"])

    voice = json.dumps(profile.get("brand_voice", {}))
    audience = json.dumps(profile.get("audience", {}))
    constraints = json.dumps(profile.get("constraints", {}))

    # Add platform-specific editing constraints
    platform_constraints = []
    if "linkedin" in platforms:
        platform_constraints.append(
            "LinkedIn posts: Must be under 3000 characters each. "
            "Punchy, line-break heavy. No emoji bullets."
        )
    if "twitter" in platforms:
        platform_constraints.append(
            "Twitter posts: Hard 280 character limit per tweet. "
            "Threads: each tweet stands alone but builds on the last."
        )
    if "short_form" in platforms:
        platform_constraints.append(
            "Short-form scripts: 75-150 words (30-60 seconds). "
            "Hook in first 2 seconds. One idea per script."
        )

    platform_rules = "\n".join(platform_constraints)

    llm = get_llm_client()
    resp = llm.chat(
        messages=[
            {"role": "system", "content": prompts.SYSTEM},
            {"role": "user", "content": prompts.USER.format(
                voice=voice,
                audience=audience,
                constraints=constraints + "\n\nPLATFORM CONSTRAINTS:\n" + platform_rules,
                content_pack=json.dumps(content_pack, indent=2),
            )},
        ],
        model=get_model_for_step("editor"),
        temperature=0.4,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(resp["content"])
    edited_pack = result.get("edited_pack", content_pack)
    edit_summary = result.get("edit_summary", "No changes made")

    logger.info("editor: %s (platforms: %s)", edit_summary, platforms)

    return {
        "edited_pack": edited_pack,
        "current_step": "editor",
    }
