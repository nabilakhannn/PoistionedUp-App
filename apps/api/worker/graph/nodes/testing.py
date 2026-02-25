"""Node 7: Testing — run quality checks on the content pack."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from worker.graph.context import fetch_relevant_resources as _fetch_relevant_resources
from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response, set_tracking_context, safe_node
from worker.graph.prompts import testing as prompts

logger = logging.getLogger("worker.graph.nodes.testing")


@safe_node
def testing(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run quality checks on the edited content pack across all platforms."""
    _tier = state.get("settings", {}).get("model_tier", "")
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "testing", _tier)

    edited_pack = state.get("edited_pack", state.get("content_pack", {}))
    profile = state.get("profile_snapshot", {})
    settings = state.get("settings", {})
    platforms = settings.get("platforms", ["youtube"])

    # Fetch relevant resources via semantic search
    user_id = state.get("user_id", "")
    content_summary = edited_pack.get("youtube_long", {}).get("title_used", "content quality check")
    gold_resources = _fetch_relevant_resources(content_summary, user_id)

    # Build platform-specific test instructions
    platform_checks = []
    if "linkedin" in platforms and edited_pack.get("linkedin_posts"):
        platform_checks.append(
            "LinkedIn posts: Check each post is under 3000 characters. "
            "Check hook line is compelling. Check for emoji bullets (should not have them)."
        )
    if "twitter" in platforms and edited_pack.get("twitter_posts"):
        platform_checks.append(
            "Twitter posts: Verify each tweet is under 280 characters (HARD FAIL if over). "
            "Thread tweets should build on each other."
        )
    if "short_form" in platforms and edited_pack.get("short_form_scripts"):
        platform_checks.append(
            "Short-form scripts: Verify 75-150 words (30-60 seconds). "
            "Hook must be in first 2 seconds. Check for on_screen_text."
        )

    extra_checks = "\n".join(platform_checks)
    extended_user = prompts.USER.format(
        profile=json.dumps(profile, indent=2),
        content_pack=json.dumps(edited_pack, indent=2),
        gold_resources=gold_resources,
    )
    if extra_checks:
        extended_user += "\n\nADDITIONAL PLATFORM CHECKS:\n" + extra_checks

    llm = get_llm_client()
    resp = llm.chat(
        messages=[
            {"role": "system", "content": prompts.SYSTEM},
            {"role": "user", "content": extended_user},
        ],
        model=get_model_for_step("testing"),
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = parse_json_response(resp["content"])
    test_results = result.get("test_results", [])
    overall_passed = result.get("overall_passed", True)

    failed_count = sum(1 for t in test_results if not t.get("passed", True))
    logger.info(
        "testing: %d tests run, %d passed, %d failed, overall=%s (platforms: %s)",
        len(test_results),
        len(test_results) - failed_count,
        failed_count,
        "PASS" if overall_passed else "FAIL",
        platforms,
    )

    return {
        "test_report": test_results,
        "tests_passed": overall_passed,
        "current_step": "testing",
    }
