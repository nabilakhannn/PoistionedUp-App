"""Agent Bridge API: OpenClaw agents <-> PositionedUp brain.

This router provides server-to-server endpoints that OpenClaw agents
call to read brand context, search knowledge, report findings, and
trigger content pipelines. Authenticated via API key (not JWT).

Usage by OpenClaw agents:
  curl -H "X-Agent-Key: $AGENT_API_KEY" \
       https://api.positionedup.com/agent-api/context/$BRAND_ID
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from app.config import settings
from app.deps import get_admin_client
from app.schemas.agent_bridge import (
    AgentHeartbeat,
    AgentReport,
    AgentReportResponse,
    BrandContext,
    InspoSearchRequest,
    KnowledgeChunk,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    PipelineTriggerRequest,
    PipelineTriggerResponse,
    TaskBoardEntry,
    TaskSyncRequest,
    TaskSyncResponse,
)

logger = logging.getLogger("app.routers.agent_bridge")

router = APIRouter(prefix="/agent-api", tags=["agent-bridge"])


# ── Auth dependency (API key) ─────────────────────────────

class AgentCaller:
    """Represents the authenticated agent/user calling the API."""
    def __init__(self, user_id: str):
        self.user_id = user_id


async def get_agent_caller(
    x_agent_key: str = Header(..., description="Agent API key"),
    x_user_id: Optional[str] = Header(None, description="User ID the agent acts on behalf of"),
) -> AgentCaller:
    """Validate agent API key and resolve user context.

    Agents pass the shared AGENT_API_KEY in the X-Agent-Key header.
    They also pass X-User-Id to identify which user's data to access.
    """
    if not settings.agent_api_key:
        raise HTTPException(503, "Agent API not configured. Set AGENT_API_KEY in env.")

    if x_agent_key != settings.agent_api_key:
        raise HTTPException(401, "Invalid agent API key")

    if not x_user_id:
        # Try to find the single user (for single-tenant setups)
        sb = get_admin_client()
        users = sb.table("profiles").select("user_id").limit(1).execute()
        if users.data:
            return AgentCaller(user_id=users.data[0]["user_id"])
        raise HTTPException(400, "X-User-Id header required (multi-user setup)")

    # Validate that x_user_id corresponds to an existing user to prevent IDOR
    sb = get_admin_client()
    check = sb.table("profiles").select("user_id").eq("user_id", x_user_id).limit(1).execute()
    if not check.data:
        raise HTTPException(404, "User not found")

    return AgentCaller(user_id=x_user_id)


# ── 1. Brand Context (the full brain dump) ────────────────

@router.get("/context/{brand_id}", response_model=BrandContext)
async def get_brand_context(brand_id: str, caller: AgentCaller = Depends(get_agent_caller)):
    """Return everything an agent needs to know about a brand.

    Single call that aggregates:
    - Brand profile (all 8 modules)
    - Completeness score
    - Recent agent memories (latest 15)
    - Performance summary (top patterns, engagement stats)
    - Voice DNA
    - Active experiments
    - Writing style rules
    """
    sb = get_admin_client()

    # 1. Brand profile
    brand_resp = (
        sb.table("personal_brands")
        .select("*")
        .eq("user_id", caller.user_id)
        .eq("id", brand_id)
        .execute()
    )
    if not brand_resp.data:
        raise HTTPException(404, f"Brand {brand_id} not found")
    brand = brand_resp.data[0]
    profile = brand.get("profile_json") or {}

    # 2. Completeness
    from app.services.brand_chat import calculate_completeness
    completeness = calculate_completeness(profile)

    # 3. Recent memories
    mem_resp = (
        sb.table("agent_memory")
        .select("id, memory_type, content, created_at")
        .eq("user_id", caller.user_id)
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(15)
        .execute()
    )

    # 4. Performance summary
    perf_data = {}
    try:
        posts = (
            sb.table("content_posts")
            .select("*")
            .eq("user_id", caller.user_id)
            .eq("brand_id", brand_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        post_list = posts.data or []
        if post_list:
            total_eng = sum(p.get("engagement_rate", 0) or 0 for p in post_list)
            avg_eng = total_eng / len(post_list) if post_list else 0
            tiers = {}
            for p in post_list:
                t = p.get("performance_tier", "unknown")
                tiers[t] = tiers.get(t, 0) + 1
            perf_data = {
                "total_posts": len(post_list),
                "avg_engagement_rate": round(avg_eng, 2),
                "tier_distribution": tiers,
                "top_posts": [
                    {"title": p.get("title", ""), "engagement_rate": p.get("engagement_rate", 0), "platform": p.get("platform", "")}
                    for p in sorted(post_list, key=lambda x: x.get("engagement_rate", 0) or 0, reverse=True)[:5]
                ],
            }
    except Exception as e:
        logger.warning("Failed to load performance data: %s", e)

    # 5. Voice DNA
    voice_data = {}
    try:
        voice_resp = (
            sb.table("agent_memory")
            .select("content")
            .eq("user_id", caller.user_id)
            .eq("brand_id", brand_id)
            .eq("memory_type", "voice_dna")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if voice_resp.data:
            import json
            try:
                voice_data = json.loads(voice_resp.data[0].get("content", "{}"))
            except (json.JSONDecodeError, TypeError):
                voice_data = {"raw": voice_resp.data[0].get("content", "")}
    except Exception as e:
        logger.warning("Failed to load voice DNA: %s", e)

    # 6. Active experiments
    exp_data = []
    try:
        exp_resp = (
            sb.table("agent_experiments")
            .select("id, hypothesis, status, variable, winner, created_at")
            .eq("user_id", caller.user_id)
            .eq("brand_id", brand_id)
            .in_("status", ["active", "proposed"])
            .execute()
        )
        exp_data = exp_resp.data or []
    except Exception as e:
        logger.warning("Failed to load experiments: %s", e)

    # 7. Content pillars from profile
    pillars = []
    if isinstance(profile, dict):
        messaging = profile.get("messaging", {})
        if isinstance(messaging, dict):
            pillars = messaging.get("content_pillars", []) or messaging.get("content_themes", []) or []

    # 8. Writing rules
    try:
        from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES
        writing_rules = HUMAN_WRITING_RULES
    except ImportError:
        writing_rules = ""

    return BrandContext(
        brand_id=brand_id,
        brand_name=brand.get("name", "Unknown"),
        completeness_pct=completeness,
        profile=profile,
        recent_memories=mem_resp.data or [],
        performance_summary=perf_data,
        voice_dna=voice_data,
        active_experiments=exp_data,
        content_pillars=pillars,
        writing_rules=writing_rules,
    )


# ── 2. Knowledge Search ──────────────────────────────────

@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(body: KnowledgeSearchRequest, caller: AgentCaller = Depends(get_agent_caller)):
    """Semantic search across the user's knowledge base.

    Returns relevant resource chunks ranked by similarity.
    Optionally filter by brand_id and gold-only resources.
    """
    from app.services.embeddings import search_similar_chunks

    chunks = search_similar_chunks(
        query=body.query,
        user_id=caller.user_id,
        limit=body.limit * 2 if body.gold_only else body.limit,
        threshold=body.threshold,
        brand_id=body.brand_id,
    )

    if not chunks:
        return KnowledgeSearchResponse(query=body.query, results=[], total_found=0)

    # Enrich with resource metadata
    sb = get_admin_client()
    resource_ids = list({c.get("resource_id", "") for c in chunks if c.get("resource_id")})

    resource_meta = {}
    if resource_ids:
        res_resp = (
            sb.table("resources")
            .select("id, title, section, is_gold, tags")
            .in_("id", resource_ids)
            .execute()
        )
        for r in (res_resp.data or []):
            resource_meta[r["id"]] = r

    results = []
    for c in chunks:
        rid = c.get("resource_id", "")
        meta = resource_meta.get(rid, {})

        # Gold-only filter
        if body.gold_only and not meta.get("is_gold", False):
            continue

        results.append(KnowledgeChunk(
            resource_id=rid,
            resource_title=meta.get("title", "Untitled"),
            section=meta.get("section"),
            is_gold=meta.get("is_gold", False),
            chunk_text=c.get("chunk_text", ""),
            similarity=c.get("similarity", 0),
            tags=meta.get("tags") or [],
        ))

    # Trim to limit after filtering
    results = results[:body.limit]

    return KnowledgeSearchResponse(
        query=body.query,
        results=results,
        total_found=len(results),
    )


# ── 3. Agent Report / Observation ─────────────────────────

@router.post("/report", response_model=AgentReportResponse)
async def submit_report(body: AgentReport, caller: AgentCaller = Depends(get_agent_caller)):
    """Agent submits a finding, observation, or deliverable.

    - Saved as an agent_message (visible in Mission Control)
    - Optionally saved as agent_memory (for future context injection)
    - If report_type is 'deliverable', also creates an agent_deliverable
    """
    sb = get_admin_client()
    response = AgentReportResponse()

    # 1. Save as message (visible in Mission Control comms)
    msg_row = {
        "user_id": caller.user_id,
        "from_agent_id": body.agent_id,
        "to_agent_id": None,
        "message": f"**{body.title}**\n\n{body.content}",
        "message_type": body.report_type,
        "task_id": body.task_id,
        "metadata": {"tags": body.tags, "brand_id": body.brand_id},
    }
    msg_resp = sb.table("agent_messages").insert(msg_row).execute()
    if msg_resp.data:
        response.message_id = msg_resp.data[0].get("id")

    # 2. Save as agent memory (for context injection in future content)
    if body.save_to_memory and body.brand_id:
        mem_type_map = {
            "observation": "observation",
            "finding": "observation",
            "insight": "lesson",
            "status_update": "observation",
            "deliverable": "observation",
        }
        mem_row = {
            "user_id": caller.user_id,
            "brand_id": body.brand_id,
            "memory_type": mem_type_map.get(body.report_type, "observation"),
            "content": f"{body.title}: {body.content}",
        }
        try:
            mem_resp = sb.table("agent_memory").insert(mem_row).execute()
            if mem_resp.data:
                response.memory_id = mem_resp.data[0].get("id")
        except Exception as e:
            logger.warning("Failed to save to agent memory: %s", e)

    # 3. If deliverable, create the deliverable record
    if body.report_type == "deliverable" and body.task_id:
        deliv_row = {
            "user_id": caller.user_id,
            "task_id": body.task_id,
            "title": body.title,
            "content": body.content,
            "deliverable_type": "document",
            "created_by_agent_id": body.agent_id,
            "status": "review",
        }
        try:
            deliv_resp = sb.table("agent_deliverables").insert(deliv_row).execute()
            if deliv_resp.data:
                response.deliverable_id = deliv_resp.data[0].get("id")
        except Exception as e:
            logger.warning("Failed to create deliverable: %s", e)

    return response


# ── 4. Pipeline Trigger ───────────────────────────────────

@router.post("/pipeline/trigger", response_model=PipelineTriggerResponse)
async def trigger_pipeline(body: PipelineTriggerRequest, caller: AgentCaller = Depends(get_agent_caller)):
    """Agent triggers the 8-node content pipeline for a brand.

    Creates a workflow and optionally auto-executes the first segment.
    """
    sb = get_admin_client()

    # Verify brand exists and belongs to user
    brand_resp = (
        sb.table("personal_brands")
        .select("id, name, profile_json")
        .eq("user_id", caller.user_id)
        .eq("id", body.brand_id)
        .execute()
    )
    if not brand_resp.data:
        raise HTTPException(404, f"Brand {body.brand_id} not found")

    # Check brand completeness gate
    from app.services.brand_chat import calculate_completeness
    profile = brand_resp.data[0].get("profile_json") or {}
    completeness = calculate_completeness(profile)
    if completeness < 50:
        raise HTTPException(
            400,
            f"Brand completeness is {completeness}%. Need >= 50% to generate content. "
            "Complete more brand modules first."
        )

    # Create workflow
    import uuid
    workflow_id = str(uuid.uuid4())
    workflow_row = {
        "id": workflow_id,
        "user_id": caller.user_id,
        "brand_id": body.brand_id,
        "status": "queued",
        "current_step": "signal_research",
        "settings": {
            "objective": body.objective,
            "content_type": body.content_type,
            "platforms": body.platforms,
            "tone": body.tone,
            "content_length": body.content_length,
            "topic": body.topic,
        },
    }
    sb.table("workflows").insert(workflow_row).execute()

    logger.info(
        "Agent-triggered pipeline: workflow=%s brand=%s objective=%s",
        workflow_id, body.brand_id, body.objective,
    )

    return PipelineTriggerResponse(workflow_id=workflow_id, status="queued")


# ── 5. Task Sync ─────────────────────────────────────────

@router.post("/tasks/sync", response_model=TaskSyncResponse)
async def sync_tasks(body: TaskSyncRequest, caller: AgentCaller = Depends(get_agent_caller)):
    """Sync tasks from task_board.md into the database.

    Upserts: if a task with the same ID exists, update it.
    If not, create it. This keeps Mission Control in sync with
    the file-based task board that agents use locally.
    """
    sb = get_admin_client()
    created = 0
    updated = 0

    for task in body.tasks:
        # Check if exists
        existing = (
            sb.table("agent_tasks")
            .select("id")
            .eq("user_id", caller.user_id)
            .eq("id", task.id)
            .execute()
        )

        row = {
            "id": task.id,
            "user_id": caller.user_id,
            "title": task.title,
            "brief": task.brief,
            "priority": task.priority,
            "status": task.status,
            "assignee_id": task.assignee_id,
            "tags": task.tags,
            "input_ref": task.input_ref,
            "output_ref": task.output_ref,
            "notes": task.notes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if existing.data:
            sb.table("agent_tasks").update(row).eq("user_id", caller.user_id).eq("id", task.id).execute()
            updated += 1
        else:
            sb.table("agent_tasks").insert(row).execute()
            created += 1

    return TaskSyncResponse(created=created, updated=updated, total=len(body.tasks))


# ── 6. Agent Heartbeat ───────────────────────────────────

@router.post("/heartbeat")
async def agent_heartbeat(body: AgentHeartbeat, caller: AgentCaller = Depends(get_agent_caller)):
    """Agent reports its status (called every 15 min by OpenClaw heartbeat).

    Updates the agent's status and last_heartbeat_at in the database.
    """
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()

    updates = {
        "status": body.status,
        "status_reason": body.status_reason,
        "last_heartbeat_at": now,
        "updated_at": now,
    }

    result = (
        sb.table("openclaw_agents")
        .update(updates)
        .eq("user_id", caller.user_id)
        .eq("id", body.agent_id)
        .execute()
    )

    if not result.data:
        logger.warning("Heartbeat from unknown agent: %s", body.agent_id)
        return {"ok": False, "error": "Agent not found"}

    return {"ok": True, "agent_id": body.agent_id, "recorded_at": now}


# ── 7. List Brands ────────────────────────────────────────

@router.get("/brands")
async def list_user_brands(caller: AgentCaller = Depends(get_agent_caller)):
    """List all brands for the user. Agents use this to discover brand IDs."""
    sb = get_admin_client()
    result = (
        sb.table("personal_brands")
        .select("id, name, is_active, created_at, updated_at")
        .eq("user_id", caller.user_id)
        .order("is_active", desc=True)
        .execute()
    )
    return result.data or []


# ── 8. Inspo Board Search ────────────────────────────────

@router.post("/inspo/search")
async def search_inspo(body: InspoSearchRequest, caller: AgentCaller = Depends(get_agent_caller)):
    """Search inspo board items. Agents can pull inspiration for content creation."""
    sb = get_admin_client()
    q = sb.table("inspo_items").select("*").eq("user_id", caller.user_id)

    if body.brand_id:
        q = q.eq("brand_id", body.brand_id)
    if body.board_id:
        q = q.eq("board_id", body.board_id)
    if body.starred_only:
        q = q.eq("is_starred", True)
    if body.query:
        # Sanitize query: escape PostgREST special characters to prevent filter injection
        safe_query = body.query.replace("%", "").replace("(", "").replace(")", "").replace(",", "").strip()
        if safe_query:
            q = q.or_(f"title.ilike.%{safe_query}%,content.ilike.%{safe_query}%,intent_note.ilike.%{safe_query}%")

    result = q.order("created_at", desc=True).limit(body.limit).execute()
    return result.data or []


# ── 9. Get Active Brand ──────────────────────────────────

@router.get("/active-brand")
async def get_active_brand(caller: AgentCaller = Depends(get_agent_caller)):
    """Get the user's currently active brand. Quick lookup for agents."""
    sb = get_admin_client()
    result = (
        sb.table("personal_brands")
        .select("id, name, profile_json, is_active")
        .eq("user_id", caller.user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "No active brand found")
    return result.data[0]
