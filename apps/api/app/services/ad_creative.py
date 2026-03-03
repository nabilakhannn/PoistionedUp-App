"""Bulk Ad Creative Service.

Given a completed brand research session, generates 40+ ad copy variations
grouped by hook type (pain, outcome, objection, social_proof, curiosity).
Each hook type gets one focused LLM call producing 8 variations.
Results are saved to agent_deliverables for Mission Control review.
"""

from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from app.deps import get_admin_client

logger = logging.getLogger("app.services.ad_creative")

# ── Constants ──────────────────────────────────────────────────

ALL_HOOK_TYPES = ["pain", "outcome", "objection", "social_proof", "curiosity"]
ALL_PLATFORMS = ["facebook", "instagram", "linkedin"]
DEFAULT_COUNT_PER_HOOK = 8


# ── Context Builder ────────────────────────────────────────────


def _build_ad_context(brand: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the rich context from brand profile + research session."""
    results = session.get("results", {})

    voice = results.get("voice_positioning", {})
    voice_options = voice.get("voice_options", [])
    first_voice = voice_options[0] if voice_options else {}

    audience = results.get("audience_research", {})
    pain_points_raw = audience.get("pain_points", [])
    pain_points: List[str] = []
    for p in pain_points_raw[:6]:
        if isinstance(p, dict):
            pain_points.append(p.get("pain_point", str(p)))
        else:
            pain_points.append(str(p))

    goals_raw = audience.get("goals", [])
    goals: List[str] = []
    for g in goals_raw[:6]:
        if isinstance(g, dict):
            goals.append(g.get("goal", str(g)))
        else:
            goals.append(str(g))

    objections_raw = audience.get("objections", [])
    objections: List[str] = []
    for o in objections_raw[:6]:
        if isinstance(o, dict):
            objections.append(o.get("objection", str(o)))
        else:
            objections.append(str(o))

    pillars_raw = results.get("content_strategy", {}).get("content_pillars", [])
    pillars: List[str] = []
    for p in pillars_raw[:4]:
        if isinstance(p, dict):
            pillars.append(p.get("name", str(p)))
        else:
            pillars.append(str(p))

    return {
        "name": brand.get("name", ""),
        "positioning": voice.get("positioning_statement", ""),
        "it_factor": voice.get("it_factor", ""),
        "tone_words": first_voice.get("tone_words", []),
        "recommended_voice": voice.get("recommended_voice", ""),
        "niche": results.get("niche_analysis", {}).get("recommended_niche", ""),
        "pain_points": pain_points,
        "goals": goals,
        "objections": objections,
        "pillars": pillars,
        "unique_angle": voice.get("unique_angle", ""),
    }


# ── Hook Prompt Builder ────────────────────────────────────────


def _build_hook_prompt(
    hook_type: str,
    context: Dict[str, Any],
    platforms: List[str],
    count: int,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a given hook type."""
    brand_name = context["name"]
    niche = context["niche"]
    positioning = context["positioning"]
    tone_words = ", ".join(context["tone_words"]) if context["tone_words"] else "professional, authentic"

    system_prompt = (
        f"You are an expert direct-response ad copywriter specializing in personal branding for {niche}. "
        f"Brand: {brand_name}. Positioning: {positioning}. "
        f"Voice/tone: {tone_words}. "
        "Write concise, punchy ad copy that drives action. "
        "Always respond with valid JSON only — no markdown, no extra text."
    )

    platform_list = ", ".join(platforms)

    if hook_type == "pain":
        pain_list = "\n".join(f"- {p}" for p in context["pain_points"]) or "- General industry frustrations"
        user_prompt = (
            f"Generate {count} pain-point ad variations for {brand_name} targeting {niche} professionals.\n\n"
            f"Pain points to draw from:\n{pain_list}\n\n"
            f"Each variation should open with a 'Are you tired of...', 'Struggling with...', or "
            f"'Stop wasting time on...' style hook. Distribute across platforms: {platform_list}.\n\n"
            f"Return JSON: {{\"variations\": [{{\"id\": \"pain_N\", \"hook_type\": \"pain\", "
            f"\"hook_angle\": \"specific pain targeted\", \"headline\": \"max 40 chars\", "
            f"\"primary_text\": \"max 125 chars\", \"cta\": \"specific action\", \"platform\": \"platform\"}}]}}"
        )

    elif hook_type == "outcome":
        goals_list = "\n".join(f"- {g}" for g in context["goals"]) or "- Achieve professional goals"
        user_prompt = (
            f"Generate {count} outcome/aspiration ad variations for {brand_name} targeting {niche} professionals.\n\n"
            f"Goals/desired outcomes to draw from:\n{goals_list}\n\n"
            f"Each variation should open with 'Imagine finally...', 'What if you could...', or "
            f"'In 90 days you could...' style hook. Distribute across platforms: {platform_list}.\n\n"
            f"Return JSON: {{\"variations\": [{{\"id\": \"outcome_N\", \"hook_type\": \"outcome\", "
            f"\"hook_angle\": \"specific outcome targeted\", \"headline\": \"max 40 chars\", "
            f"\"primary_text\": \"max 125 chars\", \"cta\": \"specific action\", \"platform\": \"platform\"}}]}}"
        )

    elif hook_type == "objection":
        obj_list = "\n".join(f"- {o}" for o in context["objections"]) or "- Common objections"
        user_prompt = (
            f"Generate {count} objection-busting ad variations for {brand_name} targeting {niche} professionals.\n\n"
            f"Objections to address:\n{obj_list}\n\n"
            f"Each variation should open with 'You don\\'t need...', 'Even if you...', or "
            f"'No experience required...' style hook. Distribute across platforms: {platform_list}.\n\n"
            f"Return JSON: {{\"variations\": [{{\"id\": \"objection_N\", \"hook_type\": \"objection\", "
            f"\"hook_angle\": \"specific objection addressed\", \"headline\": \"max 40 chars\", "
            f"\"primary_text\": \"max 125 chars\", \"cta\": \"specific action\", \"platform\": \"platform\"}}]}}"
        )

    elif hook_type == "social_proof":
        user_prompt = (
            f"Generate {count} social proof ad variations for {brand_name} targeting {niche} professionals.\n\n"
            f"Positioning: {positioning}\n\n"
            f"Each variation should open with 'Join 1,000+ {niche}...', 'Here\\'s what happened when...', or "
            f"'[Client] went from X to Y...' style hook. Distribute across platforms: {platform_list}.\n\n"
            f"Return JSON: {{\"variations\": [{{\"id\": \"social_proof_N\", \"hook_type\": \"social_proof\", "
            f"\"hook_angle\": \"specific social proof angle\", \"headline\": \"max 40 chars\", "
            f"\"primary_text\": \"max 125 chars\", \"cta\": \"specific action\", \"platform\": \"platform\"}}]}}"
        )

    else:  # curiosity
        unique_angle = context["unique_angle"] or context["it_factor"] or f"the {niche} strategy"
        user_prompt = (
            f"Generate {count} curiosity-gap ad variations for {brand_name} targeting {niche} professionals.\n\n"
            f"Unique angle / IT factor: {unique_angle}\n\n"
            f"Each variation should open with 'The one thing {niche} never talk about...', "
            f"'Why most {niche} are doing X wrong...', or 'The secret behind...' style hook. "
            f"Distribute across platforms: {platform_list}.\n\n"
            f"Return JSON: {{\"variations\": [{{\"id\": \"curiosity_N\", \"hook_type\": \"curiosity\", "
            f"\"hook_angle\": \"specific curiosity angle\", \"headline\": \"max 40 chars\", "
            f"\"primary_text\": \"max 125 chars\", \"cta\": \"specific action\", \"platform\": \"platform\"}}]}}"
        )

    return system_prompt, user_prompt


# ── LLM Call ──────────────────────────────────────────────────


def _call_llm_for_hook(
    hook_type: str,
    context: Dict[str, Any],
    platforms: List[str],
    count: int,
) -> List[Dict[str, Any]]:
    """Run one LLM call for a hook type and return the variations list."""
    from worker.graph.llm import get_llm_client, get_model_for_chat, parse_json_response

    system_prompt, user_prompt = _build_hook_prompt(hook_type, context, platforms, count)

    llm = get_llm_client()
    model = get_model_for_chat()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = llm.chat(messages=messages, model=model, temperature=0.8, max_tokens=3000)
        raw = response.get("content", "{}")
        parsed = parse_json_response(raw)
        variations = parsed.get("variations", [])
        # Ensure all variations have the hook_type set correctly
        for v in variations:
            v["hook_type"] = hook_type
        return variations
    except Exception as e:
        # Quota / budget exceptions must propagate — never swallow them silently.
        from worker.graph.llm import DailyTokenCapExceeded, WorkflowBudgetExceeded
        if isinstance(e, (DailyTokenCapExceeded, WorkflowBudgetExceeded)):
            raise
        logger.warning("LLM call failed for hook_type=%s: %s", hook_type, e)
        return []


# ── Main Service Function ──────────────────────────────────────


def generate_bulk_ads(
    user_id: str,
    brand_id: str,
    session_id: str,
    hook_types: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    count_per_hook: int = DEFAULT_COUNT_PER_HOOK,
) -> Dict[str, Any]:
    """Generate bulk ad variations from a completed research session.

    Returns:
        {
            deliverable_id: str,
            total_count: int,
            variations_by_hook: Dict[str, List[Dict]],
            brand_name: str,
            niche: str,
        }

    Raises:
        ValueError: if session is not found or not completed.
    """
    sb = get_admin_client()

    # Resolve hook types and platforms to their defaults
    if not hook_types:
        hook_types = list(ALL_HOOK_TYPES)
    if not platforms:
        platforms = list(ALL_PLATFORMS)
    count_per_hook = max(1, min(count_per_hook, 12))

    # Load brand
    brand_resp = (
        sb.table("personal_brands")
        .select("*")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not brand_resp.data:
        raise ValueError(f"Brand {brand_id} not found")
    brand = brand_resp.data[0]

    # Load research session
    session_resp = (
        sb.table("brand_research_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not session_resp.data:
        raise ValueError(f"Research session {session_id} not found")
    session = session_resp.data[0]

    if session.get("status") != "completed":
        raise ValueError(
            f"Research session {session_id} is not completed "
            f"(status={session.get('status')}). Run all research stages first."
        )

    # Build context from research data
    context = _build_ad_context(brand, session)
    brand_name = context["name"] or brand.get("name", "Brand")
    niche = context["niche"] or "professionals"

    # ── Parallel generation (one thread per hook type) ────────────────────
    # Each hook type is independent — no data dependencies between them.
    # ThreadPoolExecutor is safe for I/O-bound LLM calls without async refactor.
    variations_by_hook: Dict[str, List[Dict[str, Any]]] = {}
    hook_errors: Dict[str, str] = {}

    def _generate_hook(hook_type: str):
        logger.info("Generating %s variations for hook_type=%s", count_per_hook, hook_type)
        return hook_type, _call_llm_for_hook(hook_type, context, platforms, count_per_hook)

    max_workers = min(len(hook_types), 5)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_generate_hook, ht): ht for ht in hook_types}
        for future in as_completed(futures):
            hook_type = futures[future]
            try:
                _, variations = future.result()
                for i, v in enumerate(variations, start=1):
                    v["id"] = f"{hook_type}_{i}"
                variations_by_hook[hook_type] = variations
            except Exception as exc:
                # Quota exceptions re-raised immediately; other failures → partial result
                from worker.graph.llm import DailyTokenCapExceeded, WorkflowBudgetExceeded
                if isinstance(exc, (DailyTokenCapExceeded, WorkflowBudgetExceeded)):
                    raise
                logger.warning("Hook %s failed: %s", hook_type, exc)
                hook_errors[hook_type] = str(exc)
                variations_by_hook[hook_type] = []

    # Preserve original hook order in the flattened list
    all_variations: List[Dict[str, Any]] = []
    for ht in hook_types:
        all_variations.extend(variations_by_hook.get(ht, []))

    total_count = len(all_variations)

    # Save to agent_deliverables
    deliverable_id = str(uuid.uuid4())
    deliverable_content = {
        "variations_by_hook": variations_by_hook,
        "all_variations": all_variations,
        "hook_errors": hook_errors,  # Empty dict when all hooks succeeded
        "context": {
            "brand_name": brand_name,
            "niche": niche,
            "session_id": session_id,
            "hook_types": hook_types,
            "platforms": platforms,
            "count_per_hook": count_per_hook,
        },
    }

    sb.table("agent_deliverables").insert({
        "id": deliverable_id,
        "user_id": user_id,
        "task_id": session_id,
        "title": f"Bulk Ad Pack — {brand_name} ({total_count} variations)",
        "content": json.dumps(deliverable_content),
        "deliverable_type": "content",
        "status": "review",
        "created_by_agent_id": "copywriter",
    }).execute()

    logger.info(
        "Generated %d ad variations for brand=%s, deliverable=%s",
        total_count, brand_id, deliverable_id,
    )

    return {
        "deliverable_id": deliverable_id,
        "total_count": total_count,
        "variations_by_hook": variations_by_hook,
        "hook_errors": hook_errors,
        "brand_name": brand_name,
        "niche": niche,
    }


def stage_approved_ads(
    user_id: str,
    brand_id: str,
    deliverable_id: str,
    variation_ids: List[str],
) -> Dict[str, Any]:
    """Stage approved ad variations as draft scheduled_items.

    Returns:
        { staged_count: int, scheduled_item_ids: List[str] }
    """
    sb = get_admin_client()

    # Load deliverable and verify ownership
    del_resp = (
        sb.table("agent_deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not del_resp.data:
        raise ValueError(f"Deliverable {deliverable_id} not found")

    deliverable = del_resp.data[0]
    try:
        content = json.loads(deliverable.get("content", "{}"))
    except (json.JSONDecodeError, TypeError):
        content = {}

    all_variations: List[Dict[str, Any]] = content.get("all_variations", [])

    # Build lookup map
    variation_map = {v["id"]: v for v in all_variations if "id" in v}

    scheduled_item_ids: List[str] = []
    items_to_insert = []

    for var_id in variation_ids:
        variation = variation_map.get(var_id)
        if not variation:
            logger.warning("Variation %s not found in deliverable %s", var_id, deliverable_id)
            continue

        item_id = str(uuid.uuid4())
        scheduled_item_ids.append(item_id)
        items_to_insert.append({
            "id": item_id,
            "user_id": user_id,
            "brand_id": brand_id,
            "title": variation.get("headline", "Ad Copy")[:500],
            "platform": variation.get("platform", "facebook"),
            "content_type": "ad_copy",
            "body_preview": variation.get("primary_text", "")[:200],
            "content_json": variation,
            "status": "draft",
        })

    if items_to_insert:
        sb.table("scheduled_items").insert(items_to_insert).execute()

    staged_count = len(scheduled_item_ids)
    logger.info(
        "Staged %d ad variations to Composer for brand=%s, deliverable=%s",
        staged_count, brand_id, deliverable_id,
    )

    return {
        "staged_count": staged_count,
        "scheduled_item_ids": scheduled_item_ids,
    }
