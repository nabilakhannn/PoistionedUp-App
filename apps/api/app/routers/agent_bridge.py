"""Agent Bridge API: OpenClaw agents <-> PositionedUp brain.

This router provides server-to-server endpoints that OpenClaw agents
call to read brand context, search knowledge, report findings, and
trigger content pipelines. Authenticated via API key (not JWT).

Usage by OpenClaw agents:
  curl -H "X-Agent-Key: $AGENT_API_KEY" \
       https://api.positionedup.com/agent-api/context/$BRAND_ID
"""

import logging
import re as _re
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
from app.schemas.notifications import AgentNotifyRequest

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

    import hmac
    if not hmac.compare_digest(x_agent_key, settings.agent_api_key):
        raise HTTPException(401, "Invalid agent API key")

    if not x_user_id:
        # OWASP A01 — single-tenant fallback: only safe in single-user deployments.
        # In multi-user production, agents MUST always pass X-User-Id.
        # Log at WARNING so ops can detect misconfigured agents calling without a user context.
        logger.warning(
            "Agent caller missing X-User-Id header — using single-tenant fallback. "
            "If this is a multi-user deployment, configure agents to always pass X-User-Id."
        )
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


async def get_user_or_agent_caller(
    request: Request,
    x_agent_key: Optional[str] = Header(None, description="Agent API key (agents only)"),
    x_user_id: Optional[str] = Header(None, description="User ID (agents only)"),
) -> AgentCaller:
    """Dual-auth: accepts EITHER X-Agent-Key (agents) OR JWT Bearer token (frontend).

    This allows the same endpoints to be called by:
    - OpenClaw agents (X-Agent-Key + X-User-Id headers)
    - Frontend (Supabase JWT in Authorization header)
    """
    # Try agent key first
    if x_agent_key:
        if not settings.agent_api_key:
            raise HTTPException(503, "Agent API not configured.")
        import hmac
        if not hmac.compare_digest(x_agent_key, settings.agent_api_key):
            raise HTTPException(401, "Invalid agent API key")
        if x_user_id:
            sb = get_admin_client()
            check = sb.table("profiles").select("user_id").eq("user_id", x_user_id).limit(1).execute()
            if not check.data:
                raise HTTPException(404, "User not found")
            return AgentCaller(user_id=x_user_id)
        # Fallback to first user
        sb = get_admin_client()
        users = sb.table("profiles").select("user_id").limit(1).execute()
        if users.data:
            return AgentCaller(user_id=users.data[0]["user_id"])
        raise HTTPException(400, "X-User-Id required")

    # Try JWT Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        if token:
            sb = get_admin_client()
            try:
                resp = sb.auth.get_user(token)
                if resp and resp.user:
                    return AgentCaller(user_id=resp.user.id)
            except Exception as exc:
                logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(401, "Invalid or expired token")

    raise HTTPException(401, "Authentication required: provide X-Agent-Key or Bearer token")


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

    # 7. Content pillars from profile (stored at profile.brand.content_pillars)
    pillars_raw: list = []
    if isinstance(profile, dict):
        brand_data = profile.get("brand", {})
        if isinstance(brand_data, dict):
            pillars_raw = brand_data.get("content_pillars", []) or brand_data.get("content_themes", []) or []
        # Fallback: check messaging section (legacy)
        if not pillars_raw:
            messaging = profile.get("messaging", {})
            if isinstance(messaging, dict):
                pillars_raw = messaging.get("content_pillars", []) or messaging.get("content_themes", []) or []
    # Normalize: pillars may be strings or {type, text} objects from LLM responses
    pillars = [
        p if isinstance(p, str) else (p.get("text", str(p)) if isinstance(p, dict) else str(p))
        for p in (pillars_raw if isinstance(pillars_raw, list) else [])
    ]

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
async def submit_report(body: AgentReport, caller: AgentCaller = Depends(get_user_or_agent_caller)):
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


# ── 4b. Pipeline Status ──────────────────────────────────

@router.get("/pipeline/{workflow_id}")
async def agent_pipeline_status(
    workflow_id: str,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Agent checks the status of a triggered pipeline/workflow."""
    sb = get_admin_client()
    resp = (
        sb.table("workflows")
        .select("id, status, current_step, error_message, updated_at")
        .eq("id", workflow_id)
        .eq("user_id", caller.user_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Workflow not found")
    return resp.data[0]


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
        # OWASP A03 — PostgREST filter injection mitigation.
        # Strict whitelist: only word chars (letters, digits), spaces and hyphens are
        # allowed. This removes PostgREST special chars (comma, dot, %, parens)
        # that could escape the `.or_()` filter string and inject extra conditions.
        safe_query = _re.sub(r"[^\w\s\-]", "", body.query, flags=_re.UNICODE).strip()[:200]
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


# ── 10. Agent Notification ─────────────────────────────────

@router.post("/notify")
async def agent_notify(body: AgentNotifyRequest, caller: AgentCaller = Depends(get_agent_caller)):
    """Agent creates a notification for the user.

    Used for briefings, alerts, reminders, and suggestions.
    """
    sb = get_admin_client()
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "user_id": caller.user_id,
        "title": body.title,
        "body": body.body,
        "notification_type": body.notification_type,
        "priority": body.priority,
        "from_agent_id": body.agent_id,
        "related_task_id": body.related_task_id,
        "action_url": body.action_url,
        "created_at": now,
    }
    resp = sb.table("agent_notifications").insert(row).execute()
    if not resp.data:
        raise HTTPException(500, "Failed to create notification")

    return {"ok": True, "notification_id": resp.data[0].get("id")}


# ── 11. QA Review ──────────────────────────────────────────

@router.post("/qa/review")
async def agent_qa_review(body: dict, caller: AgentCaller = Depends(get_agent_caller)):
    """Agent submits content for QA review.

    Expects JSON body with:
      - content_text (required): The text to review
      - platform (optional): Target platform
      - content_ref_type (optional): 'scheduled_item' | 'deliverable' | 'workflow' | 'freeform'
      - content_ref_id (optional): ID of the source content
      - brand_id (optional): Brand to check voice against
    """
    from app.schemas.qa_review import QAReviewRequest
    from app.services.qa_review import review_content

    content_text = body.get("content_text", "")
    if not content_text:
        raise HTTPException(400, "content_text is required")

    request = QAReviewRequest(
        content_text=content_text[:50000],
        platform=body.get("platform"),
        content_ref_type=body.get("content_ref_type", "freeform"),
        content_ref_id=body.get("content_ref_id"),
        brand_id=body.get("brand_id"),
    )

    sb = get_admin_client()
    result = review_content(caller.user_id, request, sb)

    return {
        "ok": True,
        "review_id": result.id,
        "overall_score": result.overall_score,
        "verdict": result.verdict,
        "feedback": result.feedback,
        "scores": result.scores.model_dump(),
        "issues": [i.model_dump() for i in result.issues],
        "revision_triggered": result.revision_triggered,
    }


# ── 12-17. Competitor Intelligence (agent-facing) ─────────────

@router.get("/competitors")
async def agent_list_competitors(
    brand_id: Optional[str] = Query(None),
    caller: AgentCaller = Depends(get_agent_caller),
):
    """List all tracked competitors for the user."""
    from app.services.competitor_intel import list_competitors

    sb = get_admin_client()
    competitors = list_competitors(caller.user_id, sb, brand_id=brand_id)
    return {"ok": True, "competitors": competitors}


@router.get("/competitors/{competitor_id}")
async def agent_get_competitor(
    competitor_id: str,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Get full competitor detail with metrics history and content."""
    from app.services.competitor_intel import get_competitor

    sb = get_admin_client()
    comp = get_competitor(competitor_id, caller.user_id, sb)
    if not comp:
        raise HTTPException(404, "Competitor not found")
    return {"ok": True, "competitor": comp}


@router.post("/competitors/{competitor_id}/analyze")
async def agent_analyze_competitor(
    competitor_id: str,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Trigger LLM analysis for a specific competitor."""
    from app.services.competitor_intel import generate_analysis_report

    sb = get_admin_client()
    report = generate_analysis_report(caller.user_id, competitor_id, sb)
    if report.get("error"):
        raise HTTPException(404, report["error"])
    return {"ok": True, "report": report}


@router.post("/competitors/{competitor_id}/refresh")
async def agent_refresh_competitor(
    competitor_id: str,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Refresh competitor data from web and recalculate threat score."""
    from app.services.competitor_intel import refresh_competitor_data

    sb = get_admin_client()
    result = refresh_competitor_data(competitor_id, caller.user_id, sb)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return {"ok": True, **result}


@router.post("/competitor-alerts")
async def agent_submit_competitor_alert(
    body: dict,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Agent submits a structured competitor alert.

    Expects JSON body with:
      - agent_id (required): Reporting agent ID
      - competitor_id (required): Competitor being reported on
      - alert_type (required): follower_surge | engagement_drop | positioning_shift | content_spike | new_strategy
      - detail (required): Human-readable alert detail (max 5000 chars)
      - metric_before (optional): Previous metric value
      - metric_after (optional): Current metric value
      - severity (optional): low | medium | high (default: medium)
      - brand_id (optional): Brand context
    """
    from datetime import datetime as dt, timezone as tz

    valid_types = {
        "follower_surge", "engagement_drop", "positioning_shift",
        "content_spike", "new_strategy",
    }
    alert_type = body.get("alert_type", "")
    if alert_type not in valid_types:
        raise HTTPException(400, f"Invalid alert_type. Valid: {sorted(valid_types)}")

    detail = (body.get("detail") or "")[:5000]
    if not detail:
        raise HTTPException(400, "detail is required")

    competitor_id = body.get("competitor_id")
    if not competitor_id:
        raise HTTPException(400, "competitor_id is required")

    severity = body.get("severity", "medium")
    if severity not in ("low", "medium", "high"):
        severity = "medium"

    # Fetch competitor name
    sb = get_admin_client()
    comp_resp = (
        sb.table("competitors")
        .select("name")
        .eq("id", competitor_id)
        .eq("user_id", caller.user_id)
        .limit(1)
        .execute()
    )
    comp_name = comp_resp.data[0]["name"] if comp_resp.data else "Unknown"

    now = dt.now(tz.utc).isoformat()
    row = {
        "user_id": caller.user_id,
        "title": f"Competitor Alert: {comp_name} — {alert_type.replace('_', ' ').title()}",
        "body": detail,
        "notification_type": "alert",
        "priority": severity,
        "from_agent_id": body.get("agent_id", "competitor-analyst"),
        "action_url": f"/mission-control/competitors/{competitor_id}",
        "metadata": {
            "competitor_id": competitor_id,
            "competitor_name": comp_name,
            "alert_type": alert_type,
            "metric_before": body.get("metric_before"),
            "metric_after": body.get("metric_after"),
        },
        "created_at": now,
    }
    resp = sb.table("agent_notifications").insert(row).execute()
    notif_id = resp.data[0]["id"] if resp.data else None

    return {"ok": True, "notification_id": notif_id, "alert_type": alert_type}


@router.post("/voice/transcribe")
async def transcribe_voice_note(
    body: dict,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Download and transcribe a Telegram voice note. Called by Jumbo agent.

    Jumbo sends the file_id from a Telegram voice message.
    The server downloads from Telegram using the server-side bot token,
    then transcribes with Whisper.

    Request body: { "file_id": "AwACAgI...", "duration_seconds": 30 }
    Response:     { "transcript": "...", "language": "en", "char_count": 123, "duration_seconds": 30, "error": "" }

    The bot_token is NEVER accepted from the request — it comes from server env only.
    """
    from app.services.voice_notes import process_telegram_voice

    file_id = body.get("file_id", "").strip()
    if not file_id:
        raise HTTPException(status_code=422, detail="file_id is required")

    duration_seconds = body.get("duration_seconds")

    bot_token = settings.telegram_bot_token
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_BOT_TOKEN not configured on server",
        )

    result = await process_telegram_voice(
        file_id=file_id,
        bot_token=bot_token,
        duration_seconds=duration_seconds,
    )

    if result.get("error"):
        # Return 200 with error field — Jumbo handles the error gracefully
        return result

    logger.info(
        "Voice note transcribed: user=%s chars=%d lang=%s",
        caller.user_id,
        result["char_count"],
        result["language"],
    )
    return result


@router.get("/competitive-landscape")
async def agent_competitive_landscape(
    brand_id: Optional[str] = Query(None),
    caller: AgentCaller = Depends(get_agent_caller),
):
    """Get aggregated competitive landscape — all competitors + gaps."""
    from app.services.competitor_intel import list_competitors, get_content_gap_analysis

    sb = get_admin_client()
    competitors = list_competitors(caller.user_id, sb, brand_id=brand_id)
    gaps = get_content_gap_analysis(caller.user_id, sb, brand_id=brand_id)

    # Build threat summary
    threat_summary = {}
    for comp in competitors:
        level = comp.get("threat_level", 3)
        threat_summary.setdefault(level, [])
        threat_summary[level].append(comp.get("name", "Unknown"))

    return {
        "ok": True,
        "total_competitors": len(competitors),
        "competitors": competitors,
        "content_gaps": gaps,
        "threat_summary": threat_summary,
    }


# ── 18. Transcript Analyze (MCP endpoint) ─────────────────

@router.post("/transcript/analyze")
async def transcript_analyze(
    body: dict,
    caller: AgentCaller = Depends(get_agent_caller),
):
    """MCP-compatible endpoint: analyze a client call transcript.

    Called from Claude.ai via REST or MCP server. Authenticates with Agent API key
    rather than JWT. Returns session_id + action plan.

    Body:
      - brand_id (required): UUID of the brand
      - transcript (required): Full call transcript text
      - call_date (optional): ISO date string
      - intake_form_id (optional): UUID of associated intake form
    """
    brand_id = body.get("brand_id", "")
    transcript = body.get("transcript", "")
    if not brand_id:
        raise HTTPException(400, "brand_id is required")
    if not transcript or len(transcript) < 10:
        raise HTTPException(400, "transcript is required and must be at least 10 characters")

    import re
    _uuid_re = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    if not _uuid_re.match(brand_id):
        raise HTTPException(400, "brand_id must be a valid UUID")

    from app.services.account_manager import analyze_transcript
    try:
        session = await analyze_transcript(
            brand_id=brand_id,
            user_id=caller.user_id,
            transcript=transcript,
            call_date=body.get("call_date"),
            intake_form_id=body.get("intake_form_id"),
        )
        return {"ok": True, **session}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(502, str(exc))


# ── 19. Activity Feed ──────────────────────────────────────


@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=100),
    caller: AgentCaller = Depends(get_user_or_agent_caller),
):
    """Return recent agent activity from agent_ledger for the activity feed panel.

    Readable by both frontend (JWT) and agents (X-Agent-Key).
    Each entry describes what an agent just did in plain English.
    """
    sb = get_admin_client()
    result = (
        sb.table("agent_ledger")
        .select("id, agent_id, task_type, summary, status, created_at, brand_id")
        .eq("user_id", caller.user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    items = []
    for row in (result.data or []):
        agent = row.get("agent_id", "agent")
        task = row.get("task_type", "task")
        summary = row.get("summary", "")
        status = row.get("status", "done")
        created_at = row.get("created_at", "")

        # Build human-readable description
        emoji = {
            "copywriter": "✍️",
            "trend-analyzer": "🔍",
            "qa-reviewer": "✅" if status == "done" else "❌",
            "competitor-analyst": "👁️",
            "distributor": "📤",
            "analytics": "📊",
            "jumbo": "🧠",
        }.get(agent, "🤖")

        items.append({
            "id": row.get("id"),
            "agent_id": agent,
            "task_type": task,
            "summary": summary[:200] if summary else f"{agent} completed {task}",
            "status": status,
            "created_at": created_at,
            "brand_id": row.get("brand_id"),
            "emoji": emoji,
        })

    return {"items": items, "total": len(items)}


# ── 20. Analytics Summary ──────────────────────────────────


@router.get("/analytics-summary")
async def get_analytics_summary(
    brand_id: Optional[str] = Query(None),
    caller: AgentCaller = Depends(get_user_or_agent_caller),
):
    """Return real analytics from agent_ledger, sdk_agent_runs, agent_deliverables.

    Readable by both frontend (JWT) and agents (X-Agent-Key).
    """
    sb = get_admin_client()

    # Validate brand_id if provided
    if brand_id:
        _uuid_pattern = _re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            _re.IGNORECASE,
        )
        if not _uuid_pattern.match(brand_id):
            raise HTTPException(400, "Invalid brand_id format")

    # Posts generated (deliverables)
    del_q = (
        sb.table("agent_deliverables")
        .select("status, qa_score, created_at")
        .eq("user_id", caller.user_id)
    )
    if brand_id:
        del_q = del_q.eq("brand_id", brand_id)
    deliverables = (del_q.execute().data or [])

    total_generated = len(deliverables)
    approved = sum(1 for d in deliverables if d.get("status") == "approved")
    rejected = sum(1 for d in deliverables if d.get("status") == "rejected")
    qa_scores = [d.get("qa_score", 0) for d in deliverables if d.get("qa_score") and d.get("qa_score") > 0]
    avg_qa = round(sum(qa_scores) / len(qa_scores), 1) if qa_scores else 0.0

    # Ledger activity
    ledger_q = (
        sb.table("agent_ledger")
        .select("agent_id, task_type, status, created_at")
        .eq("user_id", caller.user_id)
        .order("created_at", desc=True)
        .limit(200)
    )
    ledger = (ledger_q.execute().data or [])

    tasks_completed = sum(1 for l in ledger if l.get("status") == "done")
    tasks_failed = sum(1 for l in ledger if l.get("status") == "error")

    # Agent breakdown
    agent_counts: dict = {}
    for row in ledger:
        a = row.get("agent_id", "unknown")
        agent_counts[a] = agent_counts.get(a, 0) + 1

    # Rejection reasons from agent_memory
    mem_q = (
        sb.table("agent_memory")
        .select("content")
        .eq("user_id", caller.user_id)
        .ilike("content", "%voice_feedback%")
        .order("created_at", desc=True)
        .limit(20)
    )
    memories = (mem_q.execute().data or [])
    rejection_tags: dict = {}
    for m in memories:
        content = str(m.get("content", ""))
        for tag in ["Wrong voice", "Bad hook", "Needs research", "Off-topic"]:
            if tag.lower() in content.lower():
                rejection_tags[tag] = rejection_tags.get(tag, 0) + 1

    return {
        "posts": {
            "total_generated": total_generated,
            "approved": approved,
            "rejected": rejected,
            "approval_rate": round(approved / total_generated * 100, 1) if total_generated else 0.0,
            "avg_qa_score": avg_qa,
        },
        "agents": {
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
            "by_agent": agent_counts,
        },
        "rejection_reasons": rejection_tags,
    }


# ── 21. Proactive Suggestions ─────────────────────────────


@router.get("/suggestions")
async def get_proactive_suggestions(
    brand_id: Optional[str] = Query(None),
    caller: AgentCaller = Depends(get_user_or_agent_caller),
):
    """Return proactive Jumbo suggestions based on 7 trigger conditions.

    Readable by both frontend (JWT) and agents (X-Agent-Key).
    Checks: posting gaps, journal staleness, hook variety, competitor threats,
            stale approvals, new leads, low QA avg.
    Returns max 5 suggestions sorted by priority.
    """
    from app.services.proactive_triggers import get_suggestions
    try:
        suggestions = get_suggestions(caller.user_id, brand_id)
        return {"suggestions": suggestions, "total": len(suggestions)}
    except Exception as exc:
        logger.warning("get_suggestions failed user=%s: %s", caller.user_id, exc)
        return {"suggestions": [], "total": 0}
