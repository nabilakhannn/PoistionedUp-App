"""Node 5: Script generation — produce the full YouTube Content Pack."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from worker.graph.context import fetch_relevant_resources as _fetch_relevant_resources
from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response, set_tracking_context, safe_node
from worker.graph.prompts import script_generation as prompts

logger = logging.getLogger("worker.graph.nodes.script_generation")


def _format_brand_context(profile: Dict[str, Any]) -> str:
    """Extract brand positioning data for script prompts."""
    brand = profile.get("brand", {})
    if not brand:
        return "No brand positioning defined yet."

    parts = []
    if brand.get("statement"):
        parts.append(f"Brand statement: {brand['statement']}")
    it = brand.get("it_factor", {})
    if it.get("unfair_advantage"):
        parts.append(f"IT factor / unfair advantage: {it['unfair_advantage']}")
    if it.get("leverage_for_brand"):
        parts.append(f"How to use it: {it['leverage_for_brand']}")
    if brand.get("content_pillars"):
        parts.append(f"Content pillars: {', '.join(brand['content_pillars'])}")

    return "\n".join(parts) if parts else "No brand positioning defined yet."


def _format_offer_context(profile: Dict[str, Any]) -> str:
    """Extract offer data for script prompts."""
    offer = profile.get("offer", {})
    if not offer:
        return "No offer defined yet."

    parts = []
    if offer.get("what"):
        parts.append(f"Offer: {offer['what']}")
    if offer.get("target_audience"):
        parts.append(f"For: {offer['target_audience']}")
    if offer.get("differentiator"):
        parts.append(f"Differentiator: {offer['differentiator']}")
    if offer.get("past_results"):
        parts.append(f"Past results: {offer['past_results']}")
    if offer.get("first_move"):
        parts.append(f"CTA: {offer['first_move']}")

    return "\n".join(parts) if parts else "No offer defined yet."


def _fetch_memory_context(user_id: str, context_query: str = "") -> str:
    """Fetch agent memories for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.agent_memory import get_relevant_memories, format_memories_as_context
        memories = get_relevant_memories(user_id, context_query or "content writing and scripts", limit=10)
        return format_memories_as_context(memories)
    except Exception as e:
        logger.debug("Memory context unavailable: %s", e)
        return ""


def _fetch_experiment_context(user_id: str, platform: str = "") -> str:
    """Fetch active experiment context for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.experiments import get_active_experiment_context
        return get_active_experiment_context(user_id, platform=platform)
    except Exception as e:
        logger.debug("Experiment context unavailable: %s", e)
        return ""


def _fetch_self_voice_context(user_id: str) -> str:
    """Fetch user's self-voice DNA for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.services.self_voice import get_voice_baseline, format_self_voice_instructions
        voice_dna = get_voice_baseline(user_id)
        if not voice_dna:
            return ""
        return format_self_voice_instructions(voice_dna)
    except Exception as e:
        logger.debug("Self-voice context unavailable: %s", e)
        return ""


def _fetch_performance_context(user_id: str, platform: str = "") -> str:
    """Fetch performance data for prompt injection. Graceful fallback."""
    if not user_id:
        return ""
    try:
        from app.deps import get_admin_client
        admin = get_admin_client()
        resp = (
            admin.table("content_posts")
            .select("*")
            .eq("user_id", user_id)
            .order("published_at", desc=True)
            .execute()
        )
        posts = resp.data if resp.data else []
        if not posts:
            return ""
        from app.services.performance_analytics import get_performance_context
        return get_performance_context(posts, platform=platform)
    except Exception as e:
        logger.debug("Performance context unavailable: %s", e)
        return ""


@safe_node
def script_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the full Content Pack for all selected platforms."""
    _tier = state.get("settings", {}).get("model_tier", "")
    set_tracking_context(state.get("workflow_id", ""), state.get("user_id", ""), "script_generation", _tier)

    topic = state.get("selected_topic", {})
    hook = state.get("selected_hook", {})
    profile = state.get("profile_snapshot", {})
    settings = state.get("settings", {})

    # Determine which platforms to generate for
    platforms = settings.get("platforms", ["youtube"])

    voice = json.dumps(profile.get("brand_voice", {}))
    audience = json.dumps(profile.get("audience", {}))
    constraints = json.dumps(profile.get("constraints", {}))

    brand_context = _format_brand_context(profile)
    offer_context = _format_offer_context(profile)

    # Fetch relevant resources via semantic search
    user_id = state.get("user_id", "")
    gold_resources = _fetch_relevant_resources(
        topic.get("title", "") + " " + topic.get("audience_pain", ""),
        user_id,
    )

    # Fetch performance context (successful patterns for this user)
    perf_context = _fetch_performance_context(user_id, platform="youtube")

    # Fetch agent memory context (content writing preferences the agent has learned)
    memory_context = _fetch_memory_context(user_id, topic.get("title", "") + " script writing")

    llm = get_llm_client()

    # Build base system prompt additions
    extra_context = ""
    if perf_context:
        extra_context += "\n\n" + perf_context
    if memory_context:
        extra_context += "\n\n" + memory_context

    # Fetch experiment context (active A/B tests)
    exp_context = _fetch_experiment_context(user_id, platform="youtube")
    if exp_context:
        extra_context += "\n\n" + exp_context

    # Fetch user's self-voice DNA (write in THEIR voice)
    self_voice = _fetch_self_voice_context(user_id)
    if self_voice:
        extra_context += "\n\n" + self_voice

    content_pack = {}
    long_summary = topic.get("title", "")

    # ── YouTube: long script + shorts + metadata ──
    if "youtube" in platforms:
        system_long = prompts.SYSTEM_LONG + extra_context

        long_resp = llm.chat(
            messages=[
                {"role": "system", "content": system_long},
                {"role": "user", "content": prompts.USER_LONG.format(
                    topic_title=topic.get("title", ""),
                    hook_text=hook.get("hook_text", ""),
                    audience_pain=topic.get("audience_pain", ""),
                    voice=voice,
                    audience=audience,
                    constraints=constraints,
                    brand_context=brand_context,
                    offer_context=offer_context,
                    required_proof=topic.get("required_proof", ""),
                    gold_resources=gold_resources,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        long_result = parse_json_response(long_resp["content"])

        long_script = long_result.get("youtube_long", {})
        long_summary = long_script.get("title_used", topic.get("title", ""))
        if long_script.get("sections"):
            section_texts = [s.get("heading", "") for s in long_script["sections"]]
            long_summary += " -- " + ", ".join(section_texts[:3])

        shorts_resp = llm.chat(
            messages=[
                {"role": "system", "content": prompts.SYSTEM_SHORTS + extra_context},
                {"role": "user", "content": prompts.USER_SHORTS.format(
                    topic_title=topic.get("title", ""),
                    long_summary=long_summary,
                    voice=voice,
                    brand_context=brand_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        shorts_result = parse_json_response(shorts_resp["content"])

        meta_resp = llm.chat(
            messages=[
                {"role": "system", "content": prompts.SYSTEM_METADATA},
                {"role": "user", "content": prompts.USER_METADATA.format(
                    topic_title=topic.get("title", ""),
                    hook_text=hook.get("hook_text", ""),
                    script_summary=long_summary,
                    profile=json.dumps(profile, indent=2),
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        meta_result = parse_json_response(meta_resp["content"])

        content_pack["youtube_long"] = long_result.get("youtube_long", {})
        content_pack["youtube_shorts"] = shorts_result.get("youtube_shorts", [])
        content_pack["titles"] = meta_result.get("titles", [])
        content_pack["description"] = meta_result.get("description", "")
        content_pack["tags"] = meta_result.get("tags", [])
        content_pack["pinned_comment"] = meta_result.get("pinned_comment", "")
        content_pack["thumbnail_brief"] = meta_result.get("thumbnail_brief", [])

    # ── LinkedIn: 3 post variants ──
    if "linkedin" in platforms:
        from worker.graph.prompts import linkedin_post as li_prompts
        li_resp = llm.chat(
            messages=[
                {"role": "system", "content": li_prompts.SYSTEM + extra_context},
                {"role": "user", "content": li_prompts.USER.format(
                    topic_title=topic.get("title", ""),
                    audience_pain=topic.get("audience_pain", ""),
                    voice=voice,
                    brand_context=brand_context,
                    offer_context=offer_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        li_result = parse_json_response(li_resp["content"])
        content_pack["linkedin_posts"] = li_result.get("linkedin_posts", [])

    # ── Twitter/X: 3 posts + 1 thread ──
    if "twitter" in platforms:
        from worker.graph.prompts import twitter_post as tw_prompts
        tw_resp = llm.chat(
            messages=[
                {"role": "system", "content": tw_prompts.SYSTEM + extra_context},
                {"role": "user", "content": tw_prompts.USER.format(
                    topic_title=topic.get("title", ""),
                    audience_pain=topic.get("audience_pain", ""),
                    voice=voice,
                    brand_context=brand_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        tw_result = parse_json_response(tw_resp["content"])
        content_pack["twitter_posts"] = tw_result.get("twitter_posts", [])
        content_pack["twitter_thread"] = tw_result.get("twitter_thread", {})

    # ── Short-form: TikTok / Reels / Shorts scripts ──
    if "short_form" in platforms:
        from worker.graph.prompts import short_form as sf_prompts
        sf_resp = llm.chat(
            messages=[
                {"role": "system", "content": sf_prompts.SYSTEM + extra_context},
                {"role": "user", "content": sf_prompts.USER.format(
                    topic_title=topic.get("title", ""),
                    long_summary=long_summary,
                    voice=voice,
                    brand_context=brand_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        sf_result = parse_json_response(sf_resp["content"])
        content_pack["short_form_scripts"] = sf_result.get("short_form_scripts", [])

    # ── Ad Copy: multi-platform ad variants ──
    if "ad" in platforms:
        from worker.graph.prompts import ad_copy as ad_prompts
        ad_resp = llm.chat(
            messages=[
                {"role": "system", "content": ad_prompts.SYSTEM + extra_context},
                {"role": "user", "content": ad_prompts.USER.format(
                    topic_title=topic.get("title", ""),
                    audience_pain=topic.get("audience_pain", ""),
                    voice=voice,
                    brand_context=brand_context,
                    offer_context=offer_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        ad_result = parse_json_response(ad_resp["content"])
        content_pack["ad_copy"] = ad_result.get("ad_copy", [])

    # ── Carousel: LinkedIn + Instagram slide decks ──
    if "carousel" in platforms:
        from worker.graph.prompts import carousel as carousel_prompts
        carousel_resp = llm.chat(
            messages=[
                {"role": "system", "content": carousel_prompts.SYSTEM + extra_context},
                {"role": "user", "content": carousel_prompts.USER.format(
                    topic_title=topic.get("title", ""),
                    audience_pain=topic.get("audience_pain", ""),
                    voice=voice,
                    brand_context=brand_context,
                )},
            ],
            model=get_model_for_step("script_generation"),
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        carousel_result = parse_json_response(carousel_resp["content"])
        content_pack["carousel_slides"] = carousel_result.get("carousel_slides", [])

    # Log summary
    parts = []
    if "youtube_long" in content_pack:
        parts.append("long=%d sections" % len(content_pack["youtube_long"].get("sections", [])))
    if "youtube_shorts" in content_pack:
        parts.append("%d YT shorts" % len(content_pack["youtube_shorts"]))
    if "linkedin_posts" in content_pack:
        parts.append("%d LinkedIn posts" % len(content_pack["linkedin_posts"]))
    if "twitter_posts" in content_pack:
        parts.append("%d tweets" % len(content_pack["twitter_posts"]))
    if "short_form_scripts" in content_pack:
        parts.append("%d short-form" % len(content_pack["short_form_scripts"]))
    if "ad_copy" in content_pack:
        parts.append("%d ad variants" % len(content_pack["ad_copy"]))
    if "carousel_slides" in content_pack:
        parts.append("%d carousels" % len(content_pack["carousel_slides"]))

    logger.info(
        "script_generation: pack created for platforms=%s (%s)",
        platforms,
        ", ".join(parts),
    )

    return {
        "content_pack": content_pack,
        "current_step": "script_generation",
    }
