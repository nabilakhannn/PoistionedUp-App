"""Agent Memory service — persistent learning system for the AI agent.

The agent builds a notebook of observations, preferences, lessons, and
patterns discovered from interactions and performance data. These memories
are semantically searched and injected into every content generation prompt,
making the agent smarter over time.

Key functions:
  - create_memory() — store a new memory with embedding
  - get_relevant_memories() — semantic search across active memories
  - format_memories_as_context() — format for LLM prompt injection
  - approve_memory() / dismiss_memory() — approval workflow for lessons
  - create_observation_from_metrics() — auto-create from performance data
  - create_observation_from_edits() — auto-create from user corrections
  - synthesize_memories() — consolidate observations into lessons
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("app.services.agent_memory")


# ── Memory CRUD ────────────────────────────────────────────

def create_memory(
    user_id: str,
    memory_type: str,
    content: str,
    confidence: float = 0.5,
    platform: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    related_post_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    generate_embedding: bool = True,
    brand_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new agent memory and optionally compute its embedding.

    Returns the created memory row.
    """
    from app.deps import get_admin_client
    admin = get_admin_client()

    insert_data = {
        "user_id": user_id,
        "memory_type": memory_type,
        "content": content,
        "confidence": confidence,
    }

    if brand_id:
        insert_data["brand_id"] = brand_id
    if platform:
        insert_data["platform"] = platform
    if category:
        insert_data["category"] = category
    if source:
        insert_data["source"] = source
    if related_post_ids:
        insert_data["related_post_ids"] = related_post_ids
    if status:
        insert_data["status"] = status

    # Generate embedding for semantic search
    if generate_embedding:
        try:
            from app.services.embeddings import generate_embedding as gen_emb
            embedding = gen_emb(content)
            insert_data["embedding"] = embedding
        except Exception as e:
            logger.warning("Failed to generate memory embedding: %s", e)

    resp = admin.table("agent_memory").insert(insert_data).execute()
    return resp.data[0] if resp.data else {}


def get_memory_by_id(memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single memory by ID, scoped to user."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("agent_memory")
        .select("*")
        .eq("id", memory_id)
        .eq("user_id", user_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def list_memories(
    user_id: str,
    memory_type: Optional[str] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    brand_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List memories with optional filters."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    query = (
        admin.table("agent_memory")
        .select("*")
        .eq("user_id", user_id)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)
    if memory_type:
        query = query.eq("memory_type", memory_type)
    if status:
        query = query.eq("status", status)
    if platform:
        query = query.eq("platform", platform)

    resp = query.order("created_at", desc=True).execute()
    return resp.data if resp.data else []


def update_memory(
    memory_id: str,
    user_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update a memory's content or metadata. Re-embeds if content changes."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    # Re-embed if content changed
    if "content" in updates and updates["content"]:
        try:
            from app.services.embeddings import generate_embedding as gen_emb
            updates["embedding"] = gen_emb(updates["content"])
        except Exception as e:
            logger.warning("Failed to re-embed memory: %s", e)

    resp = (
        admin.table("agent_memory")
        .update(updates)
        .eq("id", memory_id)
        .eq("user_id", user_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def delete_memory(memory_id: str, user_id: str) -> bool:
    """Delete a memory. Returns True if deleted."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("agent_memory")
        .delete()
        .eq("id", memory_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(resp.data)


# ── Approval Workflow ─────────────────────────────────────

def approve_memory(memory_id: str, user_id: str, edited_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Approve a pending memory, optionally editing its content first."""
    updates = {"status": "active"}
    if edited_content:
        updates["content"] = edited_content
    return update_memory(memory_id, user_id, updates)


def dismiss_memory(memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Dismiss/reject a pending memory."""
    return update_memory(memory_id, user_id, {"status": "dismissed"})


def supersede_memory(
    old_memory_id: str,
    user_id: str,
    new_content: str,
    new_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Replace an old memory with a new one. Marks old as superseded."""
    old = get_memory_by_id(old_memory_id, user_id)
    if not old:
        raise ValueError(f"Memory {old_memory_id} not found")

    # Mark old as superseded
    update_memory(old_memory_id, user_id, {"status": "superseded"})

    # Create new memory pointing back to old
    return create_memory(
        user_id=user_id,
        memory_type=new_type or old["memory_type"],
        content=new_content,
        confidence=old.get("confidence", 0.5),
        platform=old.get("platform"),
        category=old.get("category"),
        source="synthesis",
        related_post_ids=old.get("related_post_ids", []),
    )


# ── Semantic Search ──────────────────────────────────────

def get_relevant_memories(
    user_id: str,
    context_query: str,
    platform: Optional[str] = None,
    limit: int = 10,
    threshold: float = 0.6,
    brand_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find memories relevant to the current context using semantic search.

    If brand_id is provided, filters results to only memories for that brand.
    Falls back to keyword-based retrieval if embedding search fails.
    Updates last_used_at for retrieved memories.
    """
    if not user_id or not context_query:
        return []

    try:
        from app.services.embeddings import generate_embedding
        query_embedding = generate_embedding(context_query)
    except Exception as e:
        logger.warning("Failed to generate query embedding for memory search: %s", e)
        return _fallback_memory_search(user_id, platform, limit)

    from app.deps import get_admin_client
    admin = get_admin_client()

    try:
        # Fetch extra if we need to post-filter by brand
        fetch_limit = limit * 3 if brand_id else limit
        resp = admin.rpc("match_agent_memories", {
            "query_embedding": query_embedding,
            "match_user_id": user_id,
            "match_count": fetch_limit,
            "match_threshold": threshold,
        }).execute()

        memories = resp.data or []

        # Filter by brand_id if specified
        if brand_id and memories:
            memories = [
                m for m in memories
                if not m.get("brand_id") or m["brand_id"] == brand_id
            ][:limit]

        # Filter by platform if specified
        if platform and memories:
            memories = [
                m for m in memories
                if not m.get("platform") or m["platform"] == platform
            ]

        # Update last_used_at for retrieved memories
        if memories:
            memory_ids = [m["id"] for m in memories]
            for mid in memory_ids:
                try:
                    admin.table("agent_memory").update(
                        {"last_used_at": "now()"}
                    ).eq("id", mid).execute()
                except Exception:
                    pass  # Non-critical

        return memories

    except Exception as e:
        logger.warning("Memory semantic search failed: %s", e)
        return _fallback_memory_search(user_id, platform, limit)


def _fallback_memory_search(
    user_id: str,
    platform: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Fallback: return most recent active memories when embedding search unavailable."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    try:
        query = (
            admin.table("agent_memory")
            .select("id, memory_type, content, confidence, platform, category, last_used_at")
            .eq("user_id", user_id)
            .eq("status", "active")
        )
        if platform:
            query = query.eq("platform", platform)

        resp = query.order("confidence", desc=True).limit(limit).execute()
        return resp.data if resp.data else []
    except Exception:
        return []


# ── Context Formatting for LLM ───────────────────────────

def format_memories_as_context(memories: List[Dict[str, Any]]) -> str:
    """Format retrieved memories into a text block for LLM prompt injection.

    Groups by type for readability:
      OBSERVATIONS: ...
      PREFERENCES: ...
      LESSONS: ...
      CONTENT PATTERNS: ...
      VOICE NOTES: ...
    """
    if not memories:
        return ""

    # Group by type
    grouped = defaultdict(list)
    for m in memories:
        grouped[m.get("memory_type", "observation")].append(m)

    TYPE_LABELS = {
        "observation": "OBSERVATIONS (What I've noticed about your content)",
        "preference": "YOUR PREFERENCES (What you've told me you want)",
        "lesson": "STRATEGIC LESSONS (Approved insights about your content strategy)",
        "content_pattern": "CONTENT PATTERNS (Structures that work for you)",
        "voice_note": "VOICE NOTES (Your writing style observations)",
    }

    parts = ["--- AGENT MEMORY (What I've learned about your content) ---"]

    for mem_type, label in TYPE_LABELS.items():
        items = grouped.get(mem_type, [])
        if not items:
            continue
        parts.append(f"\n{label}:")
        for item in items:
            conf = item.get("confidence", 0.5)
            conf_indicator = "high" if conf >= 0.8 else "medium" if conf >= 0.5 else "low"
            platform_tag = f" [{item['platform']}]" if item.get("platform") else ""
            parts.append(f"  - {item['content']}{platform_tag} (confidence: {conf_indicator})")

    parts.append("\nUse these memories to personalize the content you're generating.")

    return "\n".join(parts)


# ── Auto-Create Memories ──────────────────────────────────

def create_observation_from_metrics(
    user_id: str,
    post: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Auto-create an observation memory when a post's metrics reveal something interesting.

    Called after metrics are entered for a post. Creates observations like:
    - "Story hooks on YouTube consistently get 2x+ engagement"
    - "Posts about AI tools outperform other topics by 3x"
    """
    tier = post.get("performance_tier")
    if not tier:
        return None

    hook_type = post.get("hook_type", "")
    topic = post.get("topic_category", "")
    platform = post.get("platform", "")
    er = post.get("engagement_rate")

    # Only create observations for extreme performers
    if tier == "viral":
        content_parts = []
        if hook_type:
            content_parts.append(f"{hook_type} hooks")
        if topic:
            content_parts.append(f"about {topic}")
        if platform:
            content_parts.append(f"on {platform}")

        subject = " ".join(content_parts) if content_parts else "This type of content"
        er_str = f" ({round(er * 100, 2)}% engagement)" if er else ""
        content = f"{subject} went viral{er_str}. Consider creating more content like: \"{post.get('title', '')}\""

        return create_memory(
            user_id=user_id,
            memory_type="observation",
            content=content,
            confidence=0.7,
            platform=platform or None,
            category=topic or None,
            source="metrics",
            related_post_ids=[post["id"]],
        )

    elif tier == "flop":
        content_parts = []
        if hook_type:
            content_parts.append(f"{hook_type} hooks")
        if topic:
            content_parts.append(f"about {topic}")
        if platform:
            content_parts.append(f"on {platform}")

        subject = " ".join(content_parts) if content_parts else "This type of content"
        content = f"{subject} significantly underperformed. Consider avoiding this pattern: \"{post.get('title', '')}\""

        return create_memory(
            user_id=user_id,
            memory_type="observation",
            content=content,
            confidence=0.6,
            platform=platform or None,
            category=topic or None,
            source="metrics",
            related_post_ids=[post["id"]],
        )

    return None


def create_observation_from_edits(
    user_id: str,
    original_text: str,
    edited_text: str,
    context: str = "content",
) -> Optional[Dict[str, Any]]:
    """Auto-create a preference memory when user edits generated content.

    Detects patterns like:
    - User always removes rhetorical questions
    - User always shortens hooks
    - User adds personal stories
    """
    if not original_text or not edited_text:
        return None

    # Simple heuristic: if significant edit, create memory
    orig_len = len(original_text)
    edit_len = len(edited_text)

    # Skip trivial edits (less than 10% change)
    if abs(orig_len - edit_len) / max(orig_len, 1) < 0.1:
        return None

    # Use LLM to detect what kind of edit was made
    try:
        from worker.graph.llm import get_llm_client, parse_json_response

        llm = get_llm_client()
        resp = llm.chat(
            messages=[
                {"role": "system", "content": (
                    "You analyze user edits to AI-generated content to detect preferences. "
                    "Return JSON with: {\"preference\": \"short description of the editing pattern\", "
                    "\"confidence\": 0.5-0.9}"
                )},
                {"role": "user", "content": (
                    f"Original ({context}):\n{original_text[:500]}\n\n"
                    f"User's edited version:\n{edited_text[:500]}\n\n"
                    "What editing preference does this reveal?"
                )},
            ],
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        result = parse_json_response(resp["content"])
        preference = result.get("preference", "")
        confidence = result.get("confidence", 0.5)

        if preference:
            return create_memory(
                user_id=user_id,
                memory_type="preference",
                content=preference,
                confidence=confidence,
                source="user_edit",
            )

    except Exception as e:
        logger.debug("Failed to analyze edit for memory creation: %s", e)

    return None


# ── Memory Synthesis ─────────────────────────────────────

def synthesize_memories(user_id: str) -> Dict[str, Any]:
    """Consolidate observations into higher-level lessons.

    Groups similar observations, detects patterns, and creates
    new 'lesson' memories (pending approval) from the evidence.
    Supersedes old observations that were consolidated.

    Returns summary of what was synthesized.
    """
    # Get all active observations
    observations = list_memories(user_id, memory_type="observation", status="active")

    if len(observations) < 3:
        return {
            "new_memories_created": 0,
            "memories_superseded": 0,
            "patterns_detected": [],
            "message": "Not enough observations to synthesize (need at least 3).",
        }

    # Group by category and platform
    by_category = defaultdict(list)
    for obs in observations:
        key = (obs.get("category", "general"), obs.get("platform", "all"))
        by_category[key].append(obs)

    new_lessons = []
    superseded_ids = []

    for (category, platform), group_obs in by_category.items():
        if len(group_obs) < 2:
            continue

        # Use LLM to synthesize observations into a lesson
        try:
            from worker.graph.llm import get_llm_client, parse_json_response

            obs_text = "\n".join([f"- {o['content']}" for o in group_obs])
            llm = get_llm_client()
            resp = llm.chat(
                messages=[
                    {"role": "system", "content": (
                        "You synthesize content observations into strategic lessons. "
                        "Write like a real person. No em dashes, no corporate filler, "
                        "no buzzwords like 'elevate' or 'leverage'. Be direct and specific. "
                        "Return JSON: {\"lesson\": \"concise strategic lesson\", "
                        "\"confidence\": 0.5-0.9, \"pattern\": \"short pattern name\"}"
                    )},
                    {"role": "user", "content": (
                        f"Category: {category}\nPlatform: {platform}\n\n"
                        f"Observations:\n{obs_text}\n\n"
                        "Synthesize these into one strategic lesson."
                    )},
                ],
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            result = parse_json_response(resp["content"])
            lesson_text = result.get("lesson", "")
            confidence = result.get("confidence", 0.6)
            pattern = result.get("pattern", "")

            if lesson_text:
                # Create lesson as pending_approval
                related_ids = []
                for o in group_obs:
                    related_ids.extend(o.get("related_post_ids", []))

                memory = create_memory(
                    user_id=user_id,
                    memory_type="lesson",
                    content=lesson_text,
                    confidence=confidence,
                    platform=platform if platform != "all" else None,
                    category=category if category != "general" else None,
                    source="synthesis",
                    related_post_ids=related_ids[:20],  # Cap at 20
                    status="pending_approval",
                )

                new_lessons.append(pattern or lesson_text[:50])

                # Mark synthesized observations as superseded
                from app.deps import get_admin_client
                admin = get_admin_client()
                for obs in group_obs:
                    admin.table("agent_memory").update(
                        {"status": "superseded"}
                    ).eq("id", obs["id"]).execute()
                    superseded_ids.append(obs["id"])

        except Exception as e:
            logger.warning("Failed to synthesize observations for %s/%s: %s", category, platform, e)

    return {
        "new_memories_created": len(new_lessons),
        "memories_superseded": len(superseded_ids),
        "patterns_detected": new_lessons,
        "message": (
            f"Synthesized {len(new_lessons)} new lessons from {len(superseded_ids)} observations. "
            "New lessons are pending your approval."
            if new_lessons
            else "No new patterns detected from current observations."
        ),
    }


# ── Auto-Record After Workflow Approval ──────────────────

def record_workflow_memories(
    user_id: str,
    workflow_id: str,
    state: Dict[str, Any],
    brand_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Auto-create memories after a workflow is approved.

    Extracts learnable signals from the completed pipeline:
      - Which topic the user chose (and why it scored well)
      - Which hook style they picked
      - What platforms they targeted
      - Any approval feedback they gave
      - The content structure that got approved

    Returns list of created memory dicts.
    """
    created = []

    selected_topic = state.get("selected_topic")
    selected_hook = state.get("selected_hook")
    goal_text = state.get("goal_text", "")
    settings = state.get("settings", {})
    platforms = settings.get("platforms", [])
    approval_feedback = state.get("rejection_feedback", "")
    objective = settings.get("objective", "")
    content_type = settings.get("content_type", "")

    # 1. Record the topic choice as an observation
    if selected_topic:
        topic_title = selected_topic.get("title", "")
        novelty = selected_topic.get("novelty_angle", "")
        score = selected_topic.get("opportunity_score", 0)

        topic_content = (
            f"User approved content about \"{topic_title}\""
        )
        if novelty:
            topic_content += f" with the angle: {novelty}"
        if score:
            topic_content += f" (opportunity score: {score}/100)"

        try:
            mem = create_memory(
                user_id=user_id,
                memory_type="observation",
                content=topic_content,
                confidence=0.6,
                category=selected_topic.get("audience_pain", ""),
                source="workflow_approval",
                related_post_ids=[workflow_id],
                brand_id=brand_id,
            )
            if mem:
                created.append(mem)
        except Exception as e:
            logger.warning("Failed to record topic memory: %s", e)

    # 2. Record the hook style preference
    if selected_hook:
        hook_text = selected_hook.get("hook_text", "")
        hook_type = selected_hook.get("hook_type", "")
        hook_score = selected_hook.get("total_score", 0)

        platform_str = ", ".join(platforms) if platforms else "general"
        hook_content = (
            f"User chose a {hook_type} hook for {platform_str} content: "
            f"\"{hook_text[:120]}\""
        )
        if hook_score:
            hook_content += f" (scored {hook_score}/100)"

        try:
            mem = create_memory(
                user_id=user_id,
                memory_type="preference",
                content=hook_content,
                confidence=0.65,
                platform=platforms[0] if platforms else None,
                source="workflow_approval",
                related_post_ids=[workflow_id],
                brand_id=brand_id,
            )
            if mem:
                created.append(mem)
        except Exception as e:
            logger.warning("Failed to record hook memory: %s", e)

    # 3. Record content objective + type combo if set
    if objective and content_type:
        combo_content = (
            f"User created {content_type} content with a {objective} objective"
        )
        if goal_text:
            combo_content += f" about: {goal_text[:100]}"

        try:
            mem = create_memory(
                user_id=user_id,
                memory_type="observation",
                content=combo_content,
                confidence=0.5,
                source="workflow_approval",
                related_post_ids=[workflow_id],
                brand_id=brand_id,
            )
            if mem:
                created.append(mem)
        except Exception as e:
            logger.warning("Failed to record objective memory: %s", e)

    # 4. Record approval feedback as a preference (if user gave feedback)
    if approval_feedback and approval_feedback.strip():
        try:
            mem = create_memory(
                user_id=user_id,
                memory_type="preference",
                content=f"User feedback on approved content: {approval_feedback.strip()[:300]}",
                confidence=0.75,
                source="workflow_approval",
                related_post_ids=[workflow_id],
                brand_id=brand_id,
            )
            if mem:
                created.append(mem)
        except Exception as e:
            logger.warning("Failed to record feedback memory: %s", e)

    # 5. Record content structure pattern from the approved pack
    pack = state.get("edited_pack") or state.get("content_pack")
    if pack:
        _record_structure_memory(user_id, workflow_id, pack, platforms, brand_id, created)

    logger.info(
        "Recorded %d memories from workflow %s approval",
        len(created), workflow_id,
    )
    return created


def _record_structure_memory(
    user_id: str,
    workflow_id: str,
    pack: Dict[str, Any],
    platforms: List[str],
    brand_id: Optional[str],
    created: List[Dict[str, Any]],
) -> None:
    """Record a content_pattern memory about the approved content structure."""
    structure_parts = []

    yt_long = pack.get("youtube_long", {})
    if yt_long:
        sections = yt_long.get("sections", [])
        headings = [s.get("heading", "") for s in sections if s.get("heading")]
        if headings:
            structure_parts.append(
                f"YouTube script with {len(sections)} sections: {', '.join(headings[:5])}"
            )

    shorts_count = len(pack.get("youtube_shorts", []))
    if shorts_count:
        structure_parts.append(f"{shorts_count} YouTube Shorts")

    li_count = len(pack.get("linkedin_posts", []))
    if li_count:
        structure_parts.append(f"{li_count} LinkedIn posts")

    tw_count = len(pack.get("twitter_posts", []))
    if tw_count:
        structure_parts.append(f"{tw_count} Twitter posts")

    sf_count = len(pack.get("short_form_scripts", []))
    if sf_count:
        structure_parts.append(f"{sf_count} short-form scripts")

    if not structure_parts:
        return

    structure_content = (
        "Approved content pack included: " + ", ".join(structure_parts)
    )

    try:
        mem = create_memory(
            user_id=user_id,
            memory_type="content_pattern",
            content=structure_content,
            confidence=0.55,
            platform=platforms[0] if platforms else None,
            source="workflow_approval",
            related_post_ids=[workflow_id],
            brand_id=brand_id,
        )
        if mem:
            created.append(mem)
    except Exception as e:
        logger.warning("Failed to record structure memory: %s", e)
