"""Mission Control router: agent dashboard, tasks, messages, deliverables."""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_user, CurrentUser
from app.deps import get_admin_client
from app.schemas.mission_control import (
    AgentCreate, AgentUpdate, AgentOut,
    TaskCreate, TaskUpdate, TaskOut,
    MessageCreate, MessageOut,
    DeliverableCreate, DeliverableOut,
    DashboardStats, OrchestratorActivity,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mission-control", tags=["mission-control"])

# ── Default agent definitions (seeded on first access) ───

DEFAULT_AGENTS = [
    {
        "id": "jarvis",
        "name": "Jarvis",
        "role": "Orchestrator",
        "role_type": "lead",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "avatar_emoji": "🎯",
        "skills": ["coordination", "decomposition", "delegation", "monitoring", "reporting"],
        "about": "Chief orchestrator of the marketing squad. Coordinates work across all agents, maintains quality standards, and makes sure nothing falls through the cracks.",
        "workspace_path": "./agents/jarvis",
    },
    {
        "id": "trend-analyzer",
        "name": "Trend Analyzer",
        "role": "Research Specialist",
        "role_type": "specialist",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "avatar_emoji": "🔍",
        "skills": ["web-search", "trend-analysis", "competitor-scan", "market-research", "data-collection"],
        "about": "Research specialist who monitors market trends, analyzes competitors, and uncovers content opportunities through web search and data analysis.",
        "workspace_path": "./agents/trend-analyzer",
    },
    {
        "id": "copywriter",
        "name": "Copywriter",
        "role": "Content Writer",
        "role_type": "specialist",
        "model_provider": "anthropic",
        "model_name": "claude-sonnet-4-20250514",
        "avatar_emoji": "✍️",
        "skills": ["carousel-scripts", "captions", "hooks", "storytelling", "copywriting"],
        "about": "Content creation specialist who writes carousels, captions, hooks, and scripts. Writes in a natural, conversational style that resonates with the target audience.",
        "workspace_path": "./agents/copywriter",
    },
    {
        "id": "visual-designer",
        "name": "Visual Designer",
        "role": "Design Specialist",
        "role_type": "specialist",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "avatar_emoji": "🎨",
        "skills": ["carousel-design", "image-creation", "templates", "brand-visuals", "mobile-first"],
        "about": "Design specialist who creates visual assets for social media. Creates carousel slides, images, and maintains brand consistency with mobile-first design.",
        "workspace_path": "./agents/visual-designer",
    },
    {
        "id": "distributor",
        "name": "Distributor",
        "role": "Publishing Specialist",
        "role_type": "specialist",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "avatar_emoji": "📤",
        "skills": ["social-media", "scheduling", "cross-platform", "posting", "distribution"],
        "about": "Publishing specialist who posts approved content to social media platforms at optimal times. Handles cross-platform formatting and scheduling.",
        "workspace_path": "./agents/distributor",
    },
    {
        "id": "analytics",
        "name": "Analytics",
        "role": "Performance Analyst",
        "role_type": "specialist",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "avatar_emoji": "📊",
        "skills": ["metrics", "reporting", "pattern-detection", "engagement-analysis", "insights"],
        "about": "Performance analyst who tracks post metrics, detects content patterns, and generates weekly performance reports. Feeds insights back into the content pipeline.",
        "workspace_path": "./agents/analytics",
    },
]


async def _ensure_agents_seeded(user_id: str, sb):
    """Seed default agents if the user has none."""
    existing = sb.table("openclaw_agents").select("id").eq("user_id", user_id).execute()
    if existing.data and len(existing.data) > 0:
        return
    for agent_def in DEFAULT_AGENTS:
        row = {**agent_def, "user_id": user_id}
        sb.table("openclaw_agents").insert(row).execute()
    logger.info("Seeded %d default agents for user %s", len(DEFAULT_AGENTS), user_id)


# ── Dashboard Stats ──────────────────────────────────────

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    await _ensure_agents_seeded(user.id, sb)

    agents = sb.table("openclaw_agents").select("id, status").eq("user_id", user.id).execute()
    tasks = sb.table("agent_tasks").select("id, status, completed_at").eq("user_id", user.id).execute()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    messages = sb.table("agent_messages").select("id", count="exact").eq("user_id", user.id).gte("created_at", today_start.isoformat()).execute()
    deliverables = sb.table("agent_deliverables").select("id", count="exact").eq("user_id", user.id).eq("status", "review").execute()

    status_counts = {}
    completed_today = 0
    for t in (tasks.data or []):
        s = t.get("status", "backlog")
        status_counts[s] = status_counts.get(s, 0) + 1
        if t.get("completed_at") and t["completed_at"] >= today_start.isoformat():
            completed_today += 1

    agents_data = agents.data or []
    return DashboardStats(
        agents_total=len(agents_data),
        agents_active=sum(1 for a in agents_data if a.get("status") == "working"),
        tasks_total=len(tasks.data or []),
        tasks_by_status=status_counts,
        tasks_completed_today=completed_today,
        messages_today=messages.count or 0,
        deliverables_pending_review=deliverables.count or 0,
    )


# ── Agent CRUD ───────────────────────────────────────────

@router.get("/agents", response_model=List[AgentOut])
async def list_agents(user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    await _ensure_agents_seeded(user.id, sb)
    result = sb.table("openclaw_agents").select("*").eq("user_id", user.id).order("role_type").execute()
    # Enrich with task counts
    tasks = sb.table("agent_tasks").select("assignee_id").eq("user_id", user.id).in_("status", ["assigned", "in_progress"]).execute()
    task_counts = {}
    for t in (tasks.data or []):
        aid = t.get("assignee_id")
        if aid:
            task_counts[aid] = task_counts.get(aid, 0) + 1
    agents = []
    for a in (result.data or []):
        a["task_count"] = task_counts.get(a["id"], 0)
        agents.append(a)
    return agents


@router.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    result = sb.table("openclaw_agents").select("*").eq("user_id", user.id).eq("id", agent_id).execute()
    if not result.data:
        raise HTTPException(404, "Agent not found")
    return result.data[0]


@router.patch("/agents/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentUpdate, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    updates = body.dict(exclude_none=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = sb.table("openclaw_agents").update(updates).eq("user_id", user.id).eq("id", agent_id).execute()
    if not result.data:
        raise HTTPException(404, "Agent not found")
    return result.data[0]


# ── Task CRUD ────────────────────────────────────────────

@router.get("/tasks", response_model=List[TaskOut])
async def list_tasks(
    status: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    sb = get_admin_client()
    q = sb.table("agent_tasks").select("*").eq("user_id", user.id)
    if status:
        q = q.eq("status", status)
    if assignee_id:
        q = q.eq("assignee_id", assignee_id)
    if priority:
        q = q.eq("priority", priority)
    result = q.order("created_at", desc=True).execute()
    return result.data or []


@router.post("/tasks", response_model=TaskOut)
async def create_task(body: TaskCreate, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    row = body.dict()
    row["user_id"] = user.id
    result = sb.table("agent_tasks").insert(row).execute()
    if not result.data:
        raise HTTPException(400, "Failed to create task")
    return result.data[0]


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    result = sb.table("agent_tasks").select("*").eq("user_id", user.id).eq("id", task_id).execute()
    if not result.data:
        raise HTTPException(404, "Task not found")
    return result.data[0]


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: str, body: TaskUpdate, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    updates = body.dict(exclude_none=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    if updates.get("status") in ("done", "archived") and "completed_at" not in updates:
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
    result = sb.table("agent_tasks").update(updates).eq("user_id", user.id).eq("id", task_id).execute()
    if not result.data:
        raise HTTPException(404, "Task not found")
    return result.data[0]


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    sb.table("agent_tasks").delete().eq("user_id", user.id).eq("id", task_id).execute()
    return {"ok": True}


# ── Messages ─────────────────────────────────────────────

@router.get("/messages", response_model=List[MessageOut])
async def list_messages(
    agent_id: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    sb = get_admin_client()
    q = sb.table("agent_messages").select("*").eq("user_id", user.id)
    if agent_id:
        q = q.or_(f"from_agent_id.eq.{agent_id},to_agent_id.eq.{agent_id}")
    if message_type:
        q = q.eq("message_type", message_type)
    if task_id:
        q = q.eq("task_id", task_id)
    result = q.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


@router.post("/messages", response_model=MessageOut)
async def create_message(body: MessageCreate, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    row = body.dict()
    row["user_id"] = user.id
    result = sb.table("agent_messages").insert(row).execute()
    if not result.data:
        raise HTTPException(400, "Failed to create message")
    return result.data[0]


# ── Deliverables ─────────────────────────────────────────

@router.get("/deliverables", response_model=List[DeliverableOut])
async def list_deliverables(
    task_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    sb = get_admin_client()
    q = sb.table("agent_deliverables").select("*").eq("user_id", user.id)
    if task_id:
        q = q.eq("task_id", task_id)
    if status:
        q = q.eq("status", status)
    result = q.order("created_at", desc=True).execute()
    return result.data or []


@router.post("/deliverables", response_model=DeliverableOut)
async def create_deliverable(body: DeliverableCreate, user: CurrentUser = Depends(get_current_user)):
    sb = get_admin_client()
    row = body.dict()
    row["user_id"] = user.id
    result = sb.table("agent_deliverables").insert(row).execute()
    if not result.data:
        raise HTTPException(400, "Failed to create deliverable")
    return result.data[0]


@router.patch("/deliverables/{deliverable_id}")
async def update_deliverable_status(
    deliverable_id: str,
    status: str = Query(...),
    feedback: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    sb = get_admin_client()
    updates = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if feedback:
        updates["feedback"] = feedback
    result = sb.table("agent_deliverables").update(updates).eq("user_id", user.id).eq("id", deliverable_id).execute()
    if not result.data:
        raise HTTPException(404, "Deliverable not found")
    return result.data[0]


# ── Orchestrator Activity (Jarvis view) ──────────────────

@router.get("/orchestrator", response_model=OrchestratorActivity)
async def get_orchestrator_activity(
    hours: int = Query(24, le=168),
    user: CurrentUser = Depends(get_current_user),
):
    sb = get_admin_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Delegations from Jarvis
    delegations = sb.table("agent_messages").select("*").eq("user_id", user.id).eq("from_agent_id", "jarvis").eq("message_type", "delegation").gte("created_at", since).order("created_at", desc=True).limit(20).execute()

    # Recent tasks created
    recent_tasks = sb.table("agent_tasks").select("*").eq("user_id", user.id).gte("created_at", since).order("created_at", desc=True).limit(20).execute()

    # Sub-agent statuses
    agents = sb.table("openclaw_agents").select("*").eq("user_id", user.id).neq("id", "jarvis").execute()

    # Full timeline (all message types)
    timeline = sb.table("agent_messages").select("*").eq("user_id", user.id).gte("created_at", since).order("created_at", desc=True).limit(50).execute()

    return OrchestratorActivity(
        delegations=delegations.data or [],
        recent_tasks_created=recent_tasks.data or [],
        sub_agent_statuses=agents.data or [],
        timeline=timeline.data or [],
    )


# ── Broadcast ────────────────────────────────────────────

@router.post("/broadcast")
async def broadcast_message(
    message: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Send a broadcast message from human to all agents."""
    sb = get_admin_client()
    row = {
        "user_id": user.id,
        "from_agent_id": None,  # human
        "to_agent_id": None,  # broadcast
        "message": message,
        "message_type": "broadcast",
    }
    result = sb.table("agent_messages").insert(row).execute()
    return {"ok": True, "message_id": result.data[0]["id"] if result.data else None}
