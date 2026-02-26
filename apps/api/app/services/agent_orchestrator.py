"""Agent Orchestrator Service: autonomous task scheduling and execution.

The orchestrator bridges the gap between schedule definitions (openclaw.json cron)
and actual task execution. It creates Mission Control tasks, delegates them to
the right backend service, and records results as deliverables.

Design:
  - Idempotent pulse: safe to call repeatedly, deduplicates via DB cooldown check
  - Task routing: maps task_type → brand_research, content pipeline, or analytics
  - Observable: all actions logged as Mission Control messages from Jumbo
  - Stateless: all state lives in Supabase, no in-memory persistence
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.deps import get_admin_client

logger = logging.getLogger("app.services.agent_orchestrator")


# ── Schedule Definitions ──────────────────────────────────────
# Internal mirror of openclaw.json cron jobs, expressed as Python
# dicts so the orchestrator can evaluate them without parsing cron.

SCHEDULES: List[Dict[str, Any]] = [
    {
        "id": "weekly_research",
        "name": "Weekly Trend Research",
        "day_of_week": 5,  # Saturday (0=Monday ... 6=Sunday)
        "hour": 10,
        "tz_offset": -5,  # EST
        "agent_id": "trend-analyzer",
        "task_type": "research",
        "priority": "P1",
        "brief": (
            "Run automated trend research for the active brand. "
            "Analyze niche trends, audience insights, and content opportunities."
        ),
        "cooldown_hours": 144,  # 6 days — prevent duplicates within week
    },
    {
        "id": "weekly_analytics",
        "name": "Weekly Analytics Report",
        "day_of_week": 6,  # Sunday
        "hour": 20,
        "tz_offset": -5,
        "agent_id": "analytics",
        "task_type": "analytics",
        "priority": "P1",
        "brief": (
            "Generate weekly performance report. "
            "Analyze post metrics, engagement trends, and content patterns."
        ),
        "cooldown_hours": 144,
    },
    {
        "id": "weekly_competitor",
        "name": "Weekly Competitor Intelligence",
        "day_of_week": 0,  # Monday
        "hour": 6,
        "tz_offset": -5,
        "agent_id": "trend-analyzer",
        "task_type": "competitor",
        "priority": "P1",
        "brief": (
            "Run competitor intelligence scan for the active brand. "
            "Analyze competitor content, positioning, and gaps."
        ),
        "cooldown_hours": 144,
    },
]


# ── Pulse (Schedule Evaluation) ──────────────────────────────

def pulse(
    user_id: str,
    *,
    auto_execute: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Evaluate schedules and create tasks for any that are due.

    Args:
        user_id: The user whose schedules to evaluate.
        auto_execute: If True, immediately execute created tasks.
        force: If True, ignore cooldown windows (for manual triggers).

    Returns:
        Dict with created_tasks, skipped, and executed results.
    """
    sb = get_admin_client()
    now = datetime.now(timezone.utc)

    created_tasks: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    executed: List[Dict[str, Any]] = []

    active_brand = _get_active_brand(user_id, sb)

    for schedule in SCHEDULES:
        sid = schedule["id"]

        if not force and not _is_schedule_due(schedule, now):
            skipped.append({"schedule_id": sid, "reason": "not_due"})
            continue

        if not force and _has_recent_task(user_id, sid, schedule["cooldown_hours"], sb):
            skipped.append({"schedule_id": sid, "reason": "cooldown"})
            continue

        if not active_brand:
            skipped.append({"schedule_id": sid, "reason": "no_active_brand"})
            continue

        task = _create_orchestrated_task(user_id, schedule, active_brand, sb)
        created_tasks.append(task)
        _log_delegation(user_id, schedule, task["id"], sb)

        if auto_execute:
            try:
                result = execute_task(task["id"], user_id)
                executed.append({"task_id": task["id"], "result": result})
            except Exception as e:
                logger.error("Auto-execution failed for task %s: %s", task["id"], e)
                executed.append({"task_id": task["id"], "error": str(e)})

    logger.info(
        "Pulse: user=%s created=%d skipped=%d executed=%d",
        user_id, len(created_tasks), len(skipped), len(executed),
    )

    return {
        "timestamp": now.isoformat(),
        "created_tasks": created_tasks,
        "skipped": skipped,
        "executed": executed,
        "active_brand": {
            "id": active_brand["id"],
            "name": active_brand["name"],
        } if active_brand else None,
    }


# ── Task Execution ────────────────────────────────────────────

def _get_handlers():
    """Lazy-load handler map to avoid forward-reference issues."""
    return {
        "research": _handle_research,
        "content": _handle_content,
        "analytics": _handle_analytics,
        "competitor": _handle_competitor,
    }


def execute_task(task_id: str, user_id: str) -> Dict[str, Any]:
    """Execute a specific orchestrator task by routing to the correct handler.

    Returns execution result dict with status and deliverable info.
    """
    sb = get_admin_client()

    resp = (
        sb.table("agent_tasks")
        .select("*")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"Task {task_id} not found")

    task = resp.data[0]

    # Extract task_type from tags (format: "type:research")
    handlers = _get_handlers()
    task_type = _extract_tag(task.get("tags") or [], "type:")
    if not task_type or task_type not in handlers:
        raise ValueError("Task has unknown or missing type")

    active_brand = _get_active_brand(user_id, sb)
    if not active_brand:
        raise ValueError("No active brand found for user")

    # Transition: assigned → in_progress
    _update_task_status(task_id, user_id, "in_progress", sb)
    _update_agent_status(task.get("assignee_id"), user_id, "working", sb)
    _log_status(user_id, task.get("assignee_id"), task_id, "started", sb)

    try:
        handler_fn = handlers[task_type]
        result = handler_fn(task, user_id, active_brand, sb)

        _update_task_status(task_id, user_id, "done", sb)
        _update_agent_status(task.get("assignee_id"), user_id, "idle", sb)
        _log_status(user_id, task.get("assignee_id"), task_id, "completed", sb)

        deliverable_id = _create_deliverable(
            user_id=user_id,
            task_id=task_id,
            title=result.get("title", f"Output: {task.get('title', '')}"),
            content=result.get("content", ""),
            deliverable_type=result.get("deliverable_type", "report"),
            agent_id=task.get("assignee_id"),
            sb=sb,
        )
        result["deliverable_id"] = deliverable_id
        result["status"] = "completed"
        return result

    except Exception as e:
        logger.error("Task execution failed: task=%s error=%s", task_id, e, exc_info=True)
        _update_task_status(task_id, user_id, "failed", sb, notes=str(e)[:500])
        _update_agent_status(task.get("assignee_id"), user_id, "error", sb)
        _log_status(
            user_id, task.get("assignee_id"), task_id,
            f"failed: {str(e)[:200]}", sb,
        )
        # Sanitize: only return safe error types, not raw exception details
        safe_msg = str(e)[:200] if isinstance(e, ValueError) else "Task execution failed"
        return {"status": "failed", "error": safe_msg}


# ── Task Type Handlers ──────────────────────────────────────────


def _handle_research(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Execute a brand research task using the 7-stage pipeline."""
    from app.services.brand_research import create_session, run_all_stages

    profile = brand.get("profile_json") or {}
    foundation = profile.get("foundation") or {}

    seed_input = {
        "name": brand["name"],
        "industry": foundation.get("industry", "general"),
        "description": brand.get("description") or foundation.get("mission", ""),
        "target_audience": (profile.get("ica") or {}).get("demographics", ""),
    }

    session = create_session(user_id, brand["id"], seed_input)
    final_session = run_all_stages(session["id"], user_id) or {}

    results = final_session.get("results") or {}
    stage_count = len(final_session.get("stages_completed") or [])

    summary_parts = [f"# Research Report: {brand['name']}\n"]
    summary_parts.append(f"**Stages completed:** {stage_count}/7\n")

    for key in [
        "niche_analysis", "audience_research", "competitive_intel",
        "content_landscape", "voice_positioning", "content_strategy",
        "content_ideas",
    ]:
        stage_data = results.get(key)
        if stage_data and not (isinstance(stage_data, dict) and stage_data.get("_skipped")):
            label = key.replace("_", " ").title()
            text = (
                stage_data.get("summary", str(stage_data)[:500])
                if isinstance(stage_data, dict)
                else str(stage_data)[:500]
            )
            summary_parts.append(f"\n## {label}\n{text}\n")

    return {
        "title": f"Trend Research Report — {brand['name']}",
        "content": "\n".join(summary_parts),
        "deliverable_type": "report",
        "research_session_id": session["id"],
        "stages_completed": stage_count,
    }


def _handle_content(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Trigger the 8-node content generation pipeline."""
    from worker.executor import run_pipeline
    from app.services.brand_chat import calculate_completeness

    profile = brand.get("profile_json") or {}
    completeness = calculate_completeness(profile)
    if completeness < 50:
        raise ValueError(
            f"Brand completeness is {completeness}%. Need >= 50% to generate content."
        )

    workflow_id = str(uuid.uuid4())
    content_settings = {
        "objective": "Create engaging content based on latest research",
        "content_type": "youtube_long",
        "platforms": ["youtube"],
        "tone": "conversational",
        "content_length": "standard",
    }

    sb.table("workflows").insert({
        "id": workflow_id,
        "user_id": user_id,
        "brand_id": brand["id"],
        "status": "queued",
        "current_step": "signal_research",
        "goal_text": content_settings["objective"],
        "settings": content_settings,
        "profile_snapshot": profile,
    }).execute()

    final_status = run_pipeline(sb, workflow_id, action="run")

    return {
        "title": f"Content Pipeline Output — {brand['name']}",
        "content": (
            f"Content pipeline completed with status: {final_status}.\n"
            f"Workflow ID: {workflow_id}"
        ),
        "deliverable_type": "content",
        "workflow_id": workflow_id,
        "pipeline_status": final_status,
    }


def _handle_analytics(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Generate a weekly analytics/performance report."""
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    workflows = (
        sb.table("workflows")
        .select("id, status, current_step, created_at")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .gte("created_at", week_ago)
        .order("created_at", desc=True)
        .execute()
    )

    schedule_items = (
        sb.table("scheduled_items")
        .select("id, status, content_type, platform")
        .eq("user_id", user_id)
        .gte("created_at", week_ago)
        .execute()
    )

    tasks = (
        sb.table("agent_tasks")
        .select("id, status, assignee_id, priority")
        .eq("user_id", user_id)
        .gte("created_at", week_ago)
        .execute()
    )

    wf_data = workflows.data or []
    sched_data = schedule_items.data or []
    task_data = tasks.data or []

    wf_by_status: Dict[str, int] = {}
    for w in wf_data:
        s = w.get("status", "unknown")
        wf_by_status[s] = wf_by_status.get(s, 0) + 1

    sched_by_status: Dict[str, int] = {}
    for s in sched_data:
        st = s.get("status", "unknown")
        sched_by_status[st] = sched_by_status.get(st, 0) + 1

    task_completed = sum(1 for t in task_data if t.get("status") == "done")
    task_total = len(task_data)
    completion_rate = (task_completed / task_total * 100) if task_total else 0

    report = (
        f"# Weekly Analytics Report — {brand['name']}\n"
        f"**Period:** {week_ago[:10]} to {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"## Content Pipeline\n"
        f"- **Workflows created:** {len(wf_data)}\n"
        f"- **By status:** {_fmt_counts(wf_by_status)}\n\n"
        f"## Content Schedule\n"
        f"- **Items created:** {len(sched_data)}\n"
        f"- **By status:** {_fmt_counts(sched_by_status)}\n\n"
        f"## Agent Activity\n"
        f"- **Tasks created:** {task_total}\n"
        f"- **Tasks completed:** {task_completed}\n"
        f"- **Completion rate:** {completion_rate:.0f}%\n"
    )

    return {
        "title": f"Weekly Analytics Report — {brand['name']}",
        "content": report,
        "deliverable_type": "report",
        "metrics": {
            "workflows": len(wf_data),
            "schedule_items": len(sched_data),
            "tasks_completed": task_completed,
        },
    }


def _handle_competitor(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Run competitor-focused research using the brand research pipeline."""
    from app.services.brand_research import create_session, run_all_stages

    profile = brand.get("profile_json") or {}
    foundation = profile.get("foundation") or {}

    seed_input = {
        "name": brand["name"],
        "industry": foundation.get("industry", "general"),
        "description": brand.get("description") or foundation.get("mission", ""),
        "target_audience": (profile.get("ica") or {}).get("demographics", ""),
    }

    session = create_session(user_id, brand["id"], seed_input)
    final_session = run_all_stages(session["id"], user_id) or {}

    results = final_session.get("results") or {}
    competitive = results.get("competitive_intel") or {}

    if isinstance(competitive, dict) and not competitive.get("_skipped"):
        summary = competitive.get("summary", str(competitive)[:1000])
    else:
        summary = "Competitive analysis was skipped or returned no results."

    return {
        "title": f"Competitor Intelligence Report — {brand['name']}",
        "content": f"# Competitor Intelligence: {brand['name']}\n\n{summary}",
        "deliverable_type": "report",
        "research_session_id": session["id"],
    }


# ── Schedule Status ─────────────────────────────────────────────

def get_status(user_id: str) -> Dict[str, Any]:
    """Get orchestrator status: schedules, active tasks, recent history."""
    sb = get_admin_client()
    now = datetime.now(timezone.utc)

    schedule_states = []
    for schedule in SCHEDULES:
        is_due = _is_schedule_due(schedule, now)
        has_recent = _has_recent_task(
            user_id, schedule["id"], schedule["cooldown_hours"], sb,
        )

        recent = (
            sb.table("agent_tasks")
            .select("id, status, created_at, completed_at")
            .eq("user_id", user_id)
            .contains("tags", [f"auto:{schedule['id']}"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        schedule_states.append({
            "id": schedule["id"],
            "name": schedule["name"],
            "agent_id": schedule["agent_id"],
            "task_type": schedule["task_type"],
            "is_due": is_due,
            "has_recent_run": has_recent,
            "last_run": recent.data[0] if recent.data else None,
        })

    active = (
        sb.table("agent_tasks")
        .select("*")
        .eq("user_id", user_id)
        .in_("status", ["assigned", "in_progress"])
        .contains("tags", ["orchestrator"])
        .order("created_at", desc=True)
        .execute()
    )

    recent_completed = (
        sb.table("agent_tasks")
        .select("*")
        .eq("user_id", user_id)
        .in_("status", ["done", "failed"])
        .contains("tags", ["orchestrator"])
        .order("completed_at", desc=True)
        .limit(10)
        .execute()
    )

    return {
        "timestamp": now.isoformat(),
        "schedules": schedule_states,
        "active_tasks": active.data or [],
        "recent_completed": recent_completed.data or [],
    }


# ── Manual Trigger ──────────────────────────────────────────────

def trigger_schedule(
    user_id: str,
    schedule_id: str,
    *,
    auto_execute: bool = True,
) -> Dict[str, Any]:
    """Manually trigger a specific schedule, ignoring cooldown."""
    sb = get_admin_client()

    schedule = next((s for s in SCHEDULES if s["id"] == schedule_id), None)
    if not schedule:
        raise ValueError(f"Unknown schedule: {schedule_id}")

    active_brand = _get_active_brand(user_id, sb)
    if not active_brand:
        raise ValueError("No active brand found")

    task = _create_orchestrated_task(user_id, schedule, active_brand, sb)
    _log_delegation(user_id, schedule, task["id"], sb)

    result: Dict[str, Any] = {"task": task}

    if auto_execute:
        try:
            result["execution"] = execute_task(task["id"], user_id)
        except Exception as e:
            result["execution"] = {"status": "failed", "error": str(e)}

    return result


# ── Internal Helpers ──────────────────────────────────────────────

def _get_active_brand(user_id: str, sb: Any) -> Optional[Dict[str, Any]]:
    """Get the user's most recently active brand."""
    resp = (
        sb.table("personal_brands")
        .select("id, name, description, profile_json, is_active")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]

    # Fallback: any brand
    resp = (
        sb.table("personal_brands")
        .select("id, name, description, profile_json, is_active")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _is_schedule_due(schedule: Dict[str, Any], now: datetime) -> bool:
    """Check if a schedule is due based on day-of-week and hour (UTC-adjusted)."""
    tz_offset = schedule.get("tz_offset", 0)
    local_now = now + timedelta(hours=tz_offset)
    return (
        local_now.weekday() == schedule["day_of_week"]
        and local_now.hour >= schedule["hour"]
    )


def _has_recent_task(
    user_id: str, schedule_id: str, cooldown_hours: int, sb: Any,
) -> bool:
    """Check if a task for this schedule was created within the cooldown window."""
    since = (datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)).isoformat()
    resp = (
        sb.table("agent_tasks")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .contains("tags", [f"auto:{schedule_id}"])
        .gte("created_at", since)
        .execute()
    )
    return (resp.count or 0) > 0


def _create_orchestrated_task(
    user_id: str,
    schedule: Dict[str, Any],
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Create a Mission Control task from a schedule definition."""
    task_id = (
        f"AUTO-{schedule['id'].upper().replace('_', '-')}"
        f"-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}"
    )
    row = {
        "id": task_id,
        "user_id": user_id,
        "title": f"{schedule['name']} — {brand['name']}",
        "brief": schedule["brief"],
        "priority": schedule["priority"],
        "status": "assigned",
        "assignee_id": schedule["agent_id"],
        "tags": [
            "orchestrator",
            f"auto:{schedule['id']}",
            f"type:{schedule['task_type']}",
        ],
        "notes": f"Auto-created by orchestrator. Brand: {brand['name']}",
    }
    resp = sb.table("agent_tasks").insert(row).execute()
    if not resp.data:
        raise RuntimeError(f"Failed to create task for schedule {schedule['id']}")
    return resp.data[0]


def _update_task_status(
    task_id: str, user_id: str, status: str, sb: Any,
    *, notes: Optional[str] = None,
) -> None:
    """Update a task's status."""
    updates: Dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if status in ("done", "failed"):
        updates["completed_at"] = datetime.now(timezone.utc).isoformat()
    if notes:
        updates["notes"] = notes
    sb.table("agent_tasks").update(updates).eq("id", task_id).eq("user_id", user_id).execute()


def _update_agent_status(
    agent_id: Optional[str], user_id: str, status: str, sb: Any,
) -> None:
    """Update an agent's status and heartbeat timestamp."""
    if not agent_id:
        return
    reason_map = {"working": "Executing orchestrator task", "idle": None, "error": "Task execution failed"}
    updates = {
        "status": status,
        "status_reason": reason_map.get(status),
        "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("openclaw_agents").update(updates).eq("id", agent_id).eq("user_id", user_id).execute()


def _log_delegation(
    user_id: str, schedule: Dict[str, Any], task_id: str, sb: Any,
) -> None:
    """Log a delegation message from Jumbo to the assigned agent."""
    sb.table("agent_messages").insert({
        "user_id": user_id,
        "from_agent_id": "jumbo",
        "to_agent_id": schedule["agent_id"],
        "message": (
            f"[Orchestrator] Delegating '{schedule['name']}' to you. "
            f"Task ID: {task_id}. Priority: {schedule['priority']}."
        ),
        "message_type": "delegation",
        "task_id": task_id,
        "metadata": {"schedule_id": schedule["id"], "auto": True},
    }).execute()


def _log_status(
    user_id: str, agent_id: Optional[str], task_id: str,
    status_text: str, sb: Any,
) -> None:
    """Log a status message from an agent back to Jumbo."""
    sb.table("agent_messages").insert({
        "user_id": user_id,
        "from_agent_id": agent_id,
        "to_agent_id": "jumbo",
        "message": f"[Status] Task {task_id}: {status_text}",
        "message_type": "status",
        "task_id": task_id,
    }).execute()


def _create_deliverable(
    user_id: str, task_id: str, title: str, content: str,
    deliverable_type: str, agent_id: Optional[str], sb: Any,
) -> Optional[str]:
    """Create a deliverable in Mission Control."""
    try:
        resp = sb.table("agent_deliverables").insert({
            "user_id": user_id,
            "task_id": task_id,
            "title": title,
            "content": content[:100000],  # respect schema max_length
            "deliverable_type": deliverable_type,
            "created_by_agent_id": agent_id,
            "status": "review",
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.warning("Failed to create deliverable: %s", e)
        return None


def _extract_tag(tags: List[str], prefix: str) -> Optional[str]:
    """Extract a value from a prefixed tag list (e.g., 'type:research' → 'research')."""
    for tag in tags:
        if tag.startswith(prefix):
            return tag[len(prefix):]
    return None


def _fmt_counts(counts: Dict[str, int]) -> str:
    """Format a {status: count} dict as a readable string."""
    return ", ".join(f"{k}: {v}" for k, v in counts.items()) or "None"
