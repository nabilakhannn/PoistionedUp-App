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
        "agent_id": "competitor-analyst",
        "task_type": "competitor",
        "priority": "P1",
        "brief": (
            "Run competitor intelligence scan for the active brand. "
            "Analyze competitor content, positioning, and gaps."
        ),
        "cooldown_hours": 144,
    },
]


# ── Daily Schedules ─────────────────────────────────────────
# These run daily (not weekly) and drive proactive behavior.

DAILY_SCHEDULES: List[Dict[str, Any]] = [
    {
        "id": "daily_briefing",
        "name": "Daily Morning Briefing",
        "hour": 8,
        "tz_offset": -5,
        "agent_id": "jumbo",
        "task_type": "daily_briefing",
        "priority": "P1",
        "brief": "Generate daily briefing: upcoming schedule, pending tasks, performance, goals, suggestions.",
        "cooldown_hours": 20,
    },
    {
        "id": "daily_content_check",
        "name": "Daily Content Calendar Check",
        "hour": 9,
        "tz_offset": -5,
        "agent_id": "jumbo",
        "task_type": "content_gap_fill",
        "priority": "P1",
        "brief": "Check content calendar for gaps in next 7 days. Suggest content to fill gaps.",
        "cooldown_hours": 20,
    },
    {
        "id": "midday_performance",
        "name": "Midday Performance Scan",
        "hour": 12,
        "tz_offset": -5,
        "agent_id": "analytics",
        "task_type": "performance_alert",
        "priority": "P2",
        "brief": "Scan for viral posts or flops published today. Create alerts for outliers.",
        "cooldown_hours": 10,
    },
    {
        "id": "evening_performance",
        "name": "Evening Performance Scan",
        "hour": 18,
        "tz_offset": -5,
        "agent_id": "analytics",
        "task_type": "performance_alert",
        "priority": "P2",
        "brief": "End-of-day performance check. Compare today vs weekly averages. Update goal progress.",
        "cooldown_hours": 10,
    },
    {
        "id": "daily_competitor_scan",
        "name": "Daily Competitor Scan",
        "hour": 7,
        "tz_offset": -5,
        "agent_id": "competitor-analyst",
        "task_type": "competitor_scan",
        "priority": "P2",
        "brief": "Refresh data for all active tracked competitors. Scan URLs and update metrics/content.",
        "cooldown_hours": 22,
    },
    {
        "id": "daily_qa_review",
        "name": "Daily QA Review",
        "hour": 10,
        "tz_offset": -5,
        "agent_id": "qa-reviewer",
        "task_type": "qa_review_pending",
        "priority": "P1",
        "brief": "Review all scheduled items in draft status that haven't been QA'd yet. Score and provide feedback.",
        "cooldown_hours": 20,
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
    notifications_created = 0

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

    # ── Daily schedules ──
    for schedule in DAILY_SCHEDULES:
        sid = schedule["id"]

        if not force and not _is_daily_due(schedule, now):
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
            agent_autonomy = _get_agent_autonomy(schedule["agent_id"], user_id, sb)
            can_auto = agent_autonomy and agent_autonomy.get("autonomy_enabled") and agent_autonomy.get("auto_execute")
            if can_auto:
                try:
                    result = execute_task(task["id"], user_id)
                    executed.append({"task_id": task["id"], "result": result})
                except Exception as e:
                    logger.error("Auto-execution failed for task %s: %s", task["id"], e)
                    executed.append({"task_id": task["id"], "error": str(e)})
            else:
                _create_notification(user_id, {
                    "title": f"Task ready: {schedule['name']}",
                    "body": f"Agent {schedule['agent_id']} wants to execute '{schedule['name']}'. Review in Mission Control.",
                    "type": "suggestion",
                    "priority": "medium",
                    "agent_id": schedule["agent_id"],
                    "task_id": task["id"],
                    "action_url": "/mission-control/orchestrator",
                }, sb)
                notifications_created += 1

    # ── Proactive condition checks ──
    proactive_findings: List[str] = []
    if active_brand:
        findings = _evaluate_proactive_conditions(user_id, active_brand, sb, force=force)
        for finding in findings:
            proactive_findings.append(finding["summary"])
            if finding.get("notification"):
                _create_notification(user_id, finding["notification"], sb)
                notifications_created += 1

    logger.info(
        "Pulse: user=%s created=%d skipped=%d executed=%d proactive=%d notifications=%d",
        user_id, len(created_tasks), len(skipped), len(executed),
        len(proactive_findings), notifications_created,
    )

    return {
        "timestamp": now.isoformat(),
        "created_tasks": created_tasks,
        "skipped": skipped,
        "executed": executed,
        "proactive_findings": proactive_findings,
        "notifications_created": notifications_created,
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
        "competitor": _handle_competitor_deep_analysis,
        "competitor_scan": _handle_competitor_scan,
        "qa_review_pending": _handle_qa_review_pending,
        "daily_briefing": _handle_daily_briefing,
        "content_gap_fill": _handle_content_gap_fill,
        "performance_alert": _handle_performance_alert,
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


def _handle_competitor_deep_analysis(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Full analysis of all competitors with threat scoring + gap analysis."""
    from app.services.competitor_intel import (
        list_competitors, generate_analysis_report,
        get_content_gap_analysis, calculate_dynamic_threat,
    )

    competitors = list_competitors(user_id, sb, brand_id=brand["id"], status="active")
    analyses = []
    threat_changes = []

    for comp in competitors[:10]:
        # Run analysis
        try:
            report = generate_analysis_report(user_id, comp["id"], sb)
            analyses.append(f"**{comp['name']}**: {report.get('summary', 'No summary')[:200]}")
        except Exception as e:
            analyses.append(f"**{comp['name']}**: Analysis failed: {str(e)[:100]}")

        # Calculate dynamic threat
        try:
            threat_result = calculate_dynamic_threat(comp["id"], user_id, sb)
            if threat_result.get("changed"):
                threat_changes.append(
                    f"{comp['name']}: {threat_result['old_level']} -> {threat_result['new_level']}"
                )
        except Exception as e:
            logger.warning("Threat scoring failed for %s: %s", comp["id"], e)

    # Content gaps
    gaps = get_content_gap_analysis(user_id, sb, brand_id=brand["id"])
    gap_count = len(gaps.get("gaps", []))

    report_text = (
        f"# Competitor Deep Analysis Report — {brand['name']}\n\n"
        f"**Competitors analyzed:** {len(competitors)}\n"
        f"**Content gaps found:** {gap_count}\n"
        f"**Threat level changes:** {len(threat_changes)}\n\n"
        "## Individual Analyses\n"
        + "\n".join(f"- {a}" for a in analyses) + "\n"
    )

    if threat_changes:
        report_text += "\n## Threat Level Changes\n" + "\n".join(f"- {c}" for c in threat_changes) + "\n"

    return {
        "title": f"Competitor Deep Analysis — {brand['name']}",
        "content": report_text,
        "deliverable_type": "report",
    }


def _handle_competitor_scan(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Refresh data for all active tracked competitors."""
    from app.services.competitor_intel import list_competitors, refresh_competitor_data

    competitors = list_competitors(user_id, sb, brand_id=brand["id"], status="active")
    refreshed = 0
    errors = 0

    for comp in competitors:
        try:
            refresh_competitor_data(comp["id"], user_id, sb)
            refreshed += 1
        except Exception as e:
            logger.warning("Failed to refresh competitor %s: %s", comp["id"], e)
            errors += 1

    return {
        "title": f"Competitor Scan — {brand['name']}",
        "content": (
            f"# Daily Competitor Scan: {brand['name']}\n\n"
            f"**Competitors scanned:** {refreshed}\n"
            f"**Errors:** {errors}\n"
            f"**Total tracked:** {len(competitors)}\n"
        ),
        "deliverable_type": "report",
    }


def _handle_qa_review_pending(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Review all draft scheduled items that haven't been QA'd yet."""
    from app.services.qa_review import review_content
    from app.schemas.qa_review import QAReviewRequest

    # Find draft items without QA reviews
    drafts_resp = (
        sb.table("scheduled_items")
        .select("id, content_body, platform, content_type")
        .eq("user_id", user_id)
        .eq("status", "draft")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    drafts = drafts_resp.data or []

    reviewed = 0
    passed = 0
    revised = 0
    failed = 0

    for item in drafts:
        content = item.get("content_body") or ""
        if not content or len(content) < 10:
            continue

        # Check if already reviewed
        existing = (
            sb.table("qa_reviews")
            .select("id")
            .eq("content_ref_type", "scheduled_item")
            .eq("content_ref_id", item["id"])
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        try:
            req = QAReviewRequest(
                content_text=content,
                platform=item.get("platform"),
                content_ref_type="scheduled_item",
                content_ref_id=item["id"],
                brand_id=brand.get("id"),
            )
            result = review_content(user_id, req, sb)
            reviewed += 1
            if result.verdict == "pass":
                passed += 1
            elif result.verdict == "revise":
                revised += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning("QA review failed for item %s: %s", item["id"], e)

    report = (
        f"# Daily QA Review — {brand['name']}\n\n"
        f"**Items reviewed:** {reviewed}\n"
        f"**Passed:** {passed}\n"
        f"**Needs revision:** {revised}\n"
        f"**Failed:** {failed}\n"
        f"**Skipped (already reviewed or empty):** {len(drafts) - reviewed}\n"
    )

    return {
        "title": f"Daily QA Review — {brand['name']}",
        "content": report,
        "deliverable_type": "report",
    }


def _handle_daily_briefing(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Generate and deliver a daily briefing."""
    result = generate_daily_briefing(user_id)
    return {
        "title": f"Daily Briefing — {brand['name']}",
        "content": result.get("briefing", ""),
        "deliverable_type": "report",
    }


def _handle_content_gap_fill(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Detect content gaps and generate suggestions."""
    now = datetime.now(timezone.utc)
    week_ahead = (now + timedelta(days=7)).isoformat()

    resp = (
        sb.table("scheduled_items")
        .select("id, content_type, platform, status, scheduled_at")
        .eq("user_id", user_id)
        .in_("status", ["scheduled", "draft"])
        .gte("scheduled_at", now.isoformat())
        .lte("scheduled_at", week_ahead)
        .order("scheduled_at")
        .execute()
    )
    items = resp.data or []

    report = (
        f"# Content Calendar Check — {brand['name']}\n\n"
        f"**Items scheduled for next 7 days:** {len(items)}\n\n"
    )

    if items:
        report += "## Scheduled Items\n"
        for item in items:
            report += f"- {item.get('content_type', '?')} on {item.get('platform', '?')} ({item.get('scheduled_at', '')[:10]})\n"
    else:
        report += "*No content scheduled. Consider creating content to fill the gap.*\n"

    if len(items) < 3:
        report += (
            f"\n## Suggestion\n"
            f"You have fewer than 3 items scheduled. Consider running the content pipeline "
            f"or drafting new posts to maintain a consistent presence.\n"
        )

    return {
        "title": f"Content Calendar Check — {brand['name']}",
        "content": report,
        "deliverable_type": "report",
    }


def _handle_performance_alert(
    task: Dict[str, Any],
    user_id: str,
    brand: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Scan for performance outliers (viral or flop posts)."""
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    today = now.replace(hour=0, minute=0, second=0).isoformat()

    # Get weekly average
    weekly_resp = (
        sb.table("content_posts")
        .select("engagement_rate")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .gte("created_at", week_ago)
        .execute()
    )
    weekly_posts = weekly_resp.data or []
    if not weekly_posts:
        return {
            "title": f"Performance Scan — {brand['name']}",
            "content": "No posts found in the last 7 days. No performance data to analyze.",
            "deliverable_type": "report",
        }

    avg_eng = sum(p.get("engagement_rate", 0) or 0 for p in weekly_posts) / len(weekly_posts)

    # Get today's posts
    today_resp = (
        sb.table("content_posts")
        .select("id, title, engagement_rate, platform, performance_tier")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .gte("created_at", today)
        .execute()
    )
    today_posts = today_resp.data or []

    report = (
        f"# Performance Scan — {brand['name']}\n\n"
        f"**7-day average engagement:** {avg_eng:.2f}%\n"
        f"**Posts today:** {len(today_posts)}\n\n"
    )

    viral = [p for p in today_posts if (p.get("engagement_rate") or 0) > avg_eng * 2]
    flops = [p for p in today_posts if 0 < (p.get("engagement_rate") or 0) < avg_eng * 0.3]

    if viral:
        report += "## Viral Posts\n"
        for p in viral:
            report += f"- **{p.get('title', 'Untitled')}** — {p.get('engagement_rate', 0):.2f}% (2x+ average)\n"

    if flops:
        report += "\n## Underperforming Posts\n"
        for p in flops:
            report += f"- {p.get('title', 'Untitled')} — {p.get('engagement_rate', 0):.2f}% (below 30% of average)\n"

    if not viral and not flops:
        report += "All posts performing within normal range.\n"

    return {
        "title": f"Performance Scan — {brand['name']}",
        "content": report,
        "deliverable_type": "report",
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

    # Daily schedules
    daily_states = []
    for schedule in DAILY_SCHEDULES:
        is_due = _is_daily_due(schedule, now)
        has_recent = _has_recent_task(
            user_id, schedule["id"], schedule["cooldown_hours"], sb,
        )
        daily_states.append({
            "id": schedule["id"],
            "name": schedule["name"],
            "agent_id": schedule["agent_id"],
            "task_type": schedule["task_type"],
            "is_due": is_due,
            "has_recent_run": has_recent,
            "last_run": None,
        })

    # Active goals
    goals_resp = (
        sb.table("agent_goals")
        .select("id, title, goal_type, target_value, current_value, target_unit, status, priority")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )

    return {
        "timestamp": now.isoformat(),
        "schedules": schedule_states,
        "daily_schedules": daily_states,
        "active_tasks": active.data or [],
        "recent_completed": recent_completed.data or [],
        "active_goals": goals_resp.data or [],
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
        schedule = next((s for s in DAILY_SCHEDULES if s["id"] == schedule_id), None)
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


def _is_daily_due(schedule: Dict[str, Any], now: datetime) -> bool:
    """Check if a daily schedule is due based on hour (UTC-adjusted)."""
    tz_offset = schedule.get("tz_offset", 0)
    local_now = now + timedelta(hours=tz_offset)
    return local_now.hour >= schedule["hour"]


def _get_agent_autonomy(agent_id: str, user_id: str, sb: Any) -> Optional[Dict[str, Any]]:
    """Get an agent's autonomy settings."""
    try:
        resp = (
            sb.table("openclaw_agents")
            .select("autonomy_enabled, confidence_threshold, auto_execute")
            .eq("id", agent_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def _create_notification(user_id: str, notification_data: Dict[str, Any], sb: Any) -> Optional[str]:
    """Create a notification for the user from an agent."""
    try:
        resp = sb.table("agent_notifications").insert({
            "user_id": user_id,
            "title": notification_data["title"],
            "body": notification_data["body"],
            "notification_type": notification_data.get("type", "insight"),
            "priority": notification_data.get("priority", "medium"),
            "from_agent_id": notification_data.get("agent_id", "jumbo"),
            "related_task_id": notification_data.get("task_id"),
            "action_url": notification_data.get("action_url"),
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        logger.warning("Failed to create notification: %s", e)
        return None


# ── Proactive Condition Checks ──────────────────────────────────


def _evaluate_proactive_conditions(
    user_id: str, brand: Dict[str, Any], sb: Any, *, force: bool = False,
) -> List[Dict[str, Any]]:
    """Evaluate proactive conditions and return findings with notifications."""
    findings: List[Dict[str, Any]] = []

    checks = [
        _check_content_gaps,
        _check_performance_drops,
        _check_stale_research,
        _check_unreviewed_deliverables,
        _check_goal_progress,
        _check_competitor_alerts,
    ]

    for check_fn in checks:
        try:
            result = check_fn(user_id, brand, sb)
            if result:
                findings.append(result)
        except Exception as e:
            logger.debug("Proactive check %s failed: %s", check_fn.__name__, e)

    return findings


def _check_content_gaps(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Check if the content calendar has gaps in the next 7 days."""
    now = datetime.now(timezone.utc)
    week_ahead = (now + timedelta(days=7)).isoformat()

    resp = (
        sb.table("scheduled_items")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .in_("status", ["scheduled", "draft"])
        .gte("scheduled_at", now.isoformat())
        .lte("scheduled_at", week_ahead)
        .execute()
    )
    count = resp.count or 0
    if count < 2:
        return {
            "summary": f"Content calendar gap: only {count} item(s) scheduled in next 7 days",
            "notification": {
                "title": "Content Calendar Gap Detected",
                "body": (
                    f"You only have {count} item(s) scheduled for the next 7 days. "
                    "Consider creating more content to maintain posting consistency."
                ),
                "type": "suggestion",
                "priority": "high" if count == 0 else "medium",
                "agent_id": "jumbo",
                "action_url": "/schedule",
            },
        }
    return None


def _check_performance_drops(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Check for week-over-week engagement drops > 15%."""
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    two_weeks_ago = (now - timedelta(days=14)).isoformat()

    # This week
    this_week = (
        sb.table("content_posts")
        .select("engagement_rate")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .gte("created_at", week_ago)
        .execute()
    )
    # Last week
    last_week = (
        sb.table("content_posts")
        .select("engagement_rate")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .gte("created_at", two_weeks_ago)
        .lt("created_at", week_ago)
        .execute()
    )

    tw_data = this_week.data or []
    lw_data = last_week.data or []

    if len(tw_data) < 2 or len(lw_data) < 2:
        return None

    tw_avg = sum(p.get("engagement_rate", 0) or 0 for p in tw_data) / len(tw_data)
    lw_avg = sum(p.get("engagement_rate", 0) or 0 for p in lw_data) / len(lw_data)

    if lw_avg > 0 and tw_avg < lw_avg * 0.85:
        drop_pct = round((1 - tw_avg / lw_avg) * 100, 1)
        return {
            "summary": f"Performance drop: engagement down {drop_pct}% week-over-week",
            "notification": {
                "title": "Engagement Drop Detected",
                "body": (
                    f"Your engagement rate dropped {drop_pct}% this week "
                    f"(from {lw_avg:.2f}% to {tw_avg:.2f}%). "
                    "Check your recent posts and consider adjusting your content strategy."
                ),
                "type": "alert",
                "priority": "high",
                "agent_id": "analytics",
                "action_url": "/performance",
            },
        }
    return None


def _check_stale_research(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Flag if the last research session is more than 14 days old."""
    two_weeks_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    resp = (
        sb.table("brand_research_sessions")
        .select("id, completed_at")
        .eq("user_id", user_id)
        .eq("brand_id", brand["id"])
        .eq("status", "completed")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        return {
            "summary": "No research sessions found — brand research is stale",
            "notification": {
                "title": "Brand Research Needed",
                "body": "No research has been run for this brand yet. Fresh research helps agents create better content.",
                "type": "suggestion",
                "priority": "medium",
                "agent_id": "trend-analyzer",
                "action_url": "/research",
            },
        }

    completed_at = resp.data[0].get("completed_at", "")
    if completed_at and completed_at < two_weeks_ago:
        return {
            "summary": "Brand research is stale (>14 days since last session)",
            "notification": {
                "title": "Research Refresh Suggested",
                "body": "Your last brand research was more than 14 days ago. Fresh insights keep content relevant.",
                "type": "suggestion",
                "priority": "low",
                "agent_id": "trend-analyzer",
                "action_url": "/research",
            },
        }
    return None


def _check_unreviewed_deliverables(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Flag deliverables pending review for more than 48 hours."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    resp = (
        sb.table("agent_deliverables")
        .select("id, title", count="exact")
        .eq("user_id", user_id)
        .eq("status", "review")
        .lte("created_at", cutoff)
        .execute()
    )
    count = resp.count or 0
    if count > 0:
        return {
            "summary": f"{count} deliverable(s) pending review for 48+ hours",
            "notification": {
                "title": f"{count} Deliverable(s) Awaiting Your Review",
                "body": (
                    f"You have {count} deliverable(s) that have been waiting for review for over 48 hours. "
                    "Approve or reject them so agents can continue their work."
                ),
                "type": "reminder",
                "priority": "medium",
                "agent_id": "jumbo",
                "action_url": "/mission-control",
            },
        }
    return None


def _check_goal_progress(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Evaluate active goals and flag if any are behind pace."""
    resp = (
        sb.table("agent_goals")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    goals = resp.data or []
    if not goals:
        return None

    behind_goals = []
    for goal in goals:
        result = evaluate_single_goal(user_id, goal, sb)
        if not result.get("on_track"):
            behind_goals.append(goal["title"])

    if behind_goals:
        return {
            "summary": f"{len(behind_goals)} goal(s) behind pace: {', '.join(behind_goals[:3])}",
            "notification": {
                "title": f"{len(behind_goals)} Goal(s) Behind Pace",
                "body": (
                    f"These goals need attention: {', '.join(behind_goals[:3])}. "
                    "Check your goals page for details."
                ),
                "type": "goal_update",
                "priority": "medium",
                "agent_id": "jumbo",
                "action_url": "/mission-control/goals",
            },
        }
    return None


def _check_competitor_alerts(
    user_id: str, brand: Dict[str, Any], sb: Any,
) -> Optional[Dict[str, Any]]:
    """Check for significant competitor metric changes (e.g. follower growth > 20%)."""
    resp = (
        sb.table("competitors")
        .select("id, name")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    competitors = resp.data or []
    if not competitors:
        return None

    alerts: List[str] = []
    for comp in competitors[:10]:  # cap to avoid excessive queries
        metrics_resp = (
            sb.table("competitor_metrics")
            .select("followers, engagement_rate, recorded_at")
            .eq("competitor_id", comp["id"])
            .order("recorded_at", desc=True)
            .limit(2)
            .execute()
        )
        snapshots = metrics_resp.data or []
        if len(snapshots) < 2:
            continue

        latest = snapshots[0].get("followers") or 0
        previous = snapshots[1].get("followers") or 0
        if previous > 0 and latest > 0:
            growth_pct = ((latest - previous) / previous) * 100
            if growth_pct > 20:
                alerts.append(
                    f"{comp['name']} gained {latest - previous:,} followers "
                    f"({growth_pct:.0f}% growth)"
                )

        # Check engagement rate drops > 15%
        latest_eng = snapshots[0].get("engagement_rate") or 0
        prev_eng = snapshots[1].get("engagement_rate") or 0
        if prev_eng > 0 and latest_eng > 0:
            eng_change = ((latest_eng - prev_eng) / prev_eng) * 100
            if eng_change < -15:
                alerts.append(
                    f"{comp['name']} engagement dropped {abs(eng_change):.0f}% "
                    f"({prev_eng:.1f}% -> {latest_eng:.1f}%)"
                )

    if alerts:
        return {
            "summary": f"Competitor alert: {alerts[0]}",
            "notification": {
                "title": "Competitor Intelligence Alert",
                "body": ". ".join(alerts[:3]) + ". Check the Competitors dashboard for details.",
                "type": "alert",
                "priority": "medium",
                "agent_id": "competitor-analyst",
                "action_url": "/mission-control/competitors",
            },
        }
    return None


def evaluate_single_goal(
    user_id: str, goal: Dict[str, Any], sb: Any,
) -> Dict[str, Any]:
    """Evaluate a single goal's progress. Returns current_value and on_track status."""
    goal_type = goal.get("goal_type", "custom")
    target = goal.get("target_value", 0)
    unit = goal.get("target_unit", "per_week")
    brand_id = goal.get("brand_id")

    now = datetime.now(timezone.utc)
    current_value = 0.0

    if goal_type == "posting_frequency":
        # Count scheduled + published items in the current period
        if unit == "per_week":
            period_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        else:
            period_start = now.replace(day=1, hour=0, minute=0, second=0)

        q = (
            sb.table("scheduled_items")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .in_("status", ["scheduled", "published"])
            .gte("created_at", period_start.isoformat())
        )
        if brand_id:
            q = q.eq("brand_id", brand_id)
        resp = q.execute()
        current_value = float(resp.count or 0)

    elif goal_type == "engagement_growth":
        # Compare current period engagement to baseline
        week_ago = (now - timedelta(days=7)).isoformat()
        q = (
            sb.table("content_posts")
            .select("engagement_rate")
            .eq("user_id", user_id)
            .gte("created_at", week_ago)
        )
        if brand_id:
            q = q.eq("brand_id", brand_id)
        resp = q.execute()
        posts = resp.data or []
        if posts:
            current_value = sum(p.get("engagement_rate", 0) or 0 for p in posts) / len(posts)

    elif goal_type == "content_pipeline":
        # Count items in scheduled queue
        q = (
            sb.table("scheduled_items")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .in_("status", ["draft", "scheduled"])
        )
        if brand_id:
            q = q.eq("brand_id", brand_id)
        resp = q.execute()
        current_value = float(resp.count or 0)

    else:
        # Custom or research_cadence — use stored current_value
        current_value = goal.get("current_value", 0)

    on_track = current_value >= target

    # Update the goal's current_value in the DB
    try:
        sb.table("agent_goals").update({
            "current_value": current_value,
            "last_evaluated_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", goal["id"]).eq("user_id", user_id).execute()
    except Exception as e:
        logger.debug("Failed to update goal progress: %s", e)

    return {"current_value": current_value, "on_track": on_track}


# ── Daily Briefing Generation ──────────────────────────────────


def generate_daily_briefing(user_id: str) -> Dict[str, Any]:
    """Generate a daily briefing notification for the user.

    Compiles: upcoming schedule, pending tasks, performance summary,
    goal progress, and proactive suggestions.
    """
    sb = get_admin_client()
    now = datetime.now(timezone.utc)
    active_brand = _get_active_brand(user_id, sb)
    brand_name = active_brand["name"] if active_brand else "your brand"

    sections = []
    sections.append(f"# Daily Briefing — {brand_name}")
    sections.append(f"*{now.strftime('%A, %B %d, %Y')}*\n")

    # 1. Upcoming scheduled content (next 3 days)
    three_days = (now + timedelta(days=3)).isoformat()
    sched_resp = (
        sb.table("scheduled_items")
        .select("id, content_type, platform, status, scheduled_at")
        .eq("user_id", user_id)
        .gte("scheduled_at", now.isoformat())
        .lte("scheduled_at", three_days)
        .order("scheduled_at")
        .limit(10)
        .execute()
    )
    sched_items = sched_resp.data or []
    if sched_items:
        sections.append("## Upcoming Content (Next 3 Days)")
        for item in sched_items:
            platform = item.get("platform", "?")
            ctype = item.get("content_type", "content")
            sched_at = item.get("scheduled_at", "")[:10]
            sections.append(f"- [{item.get('status', 'draft')}] {ctype} on {platform} — {sched_at}")
    else:
        sections.append("## Upcoming Content\n*No content scheduled for the next 3 days.*")

    # 2. Pending tasks
    task_resp = (
        sb.table("agent_tasks")
        .select("id, title, status, assignee_id, priority")
        .eq("user_id", user_id)
        .in_("status", ["assigned", "in_progress", "review"])
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    pending_tasks = task_resp.data or []
    if pending_tasks:
        sections.append(f"\n## Pending Tasks ({len(pending_tasks)})")
        for t in pending_tasks:
            sections.append(f"- [{t.get('priority', 'P2')}] {t['title']} ({t.get('status', '?')}, assigned to {t.get('assignee_id', '?')})")
    else:
        sections.append("\n## Pending Tasks\n*All clear — no pending tasks.*")

    # 3. Performance summary (last 7 days)
    if active_brand:
        week_ago = (now - timedelta(days=7)).isoformat()
        perf_resp = (
            sb.table("content_posts")
            .select("engagement_rate, performance_tier")
            .eq("user_id", user_id)
            .eq("brand_id", active_brand["id"])
            .gte("created_at", week_ago)
            .execute()
        )
        posts = perf_resp.data or []
        if posts:
            avg_eng = sum(p.get("engagement_rate", 0) or 0 for p in posts) / len(posts)
            sections.append(f"\n## Performance (7-Day)")
            sections.append(f"- **Posts analyzed:** {len(posts)}")
            sections.append(f"- **Avg engagement:** {avg_eng:.2f}%")
        else:
            sections.append("\n## Performance\n*No post data for this week.*")

    # 4. Goal progress
    goal_resp = (
        sb.table("agent_goals")
        .select("title, target_value, current_value, target_unit, status")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    goals = goal_resp.data or []
    if goals:
        sections.append(f"\n## Goals ({len(goals)} active)")
        for g in goals:
            pct = (g.get("current_value", 0) / g["target_value"] * 100) if g.get("target_value") else 0
            status_emoji = "on track" if pct >= 70 else "behind"
            sections.append(f"- **{g['title']}**: {g.get('current_value', 0)}/{g['target_value']} {g.get('target_unit', '')} ({pct:.0f}% — {status_emoji})")

    # 5. Unreviewed deliverables
    deliv_resp = (
        sb.table("agent_deliverables")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("status", "review")
        .execute()
    )
    deliv_count = deliv_resp.count or 0
    if deliv_count > 0:
        sections.append(f"\n## Action Required\n- **{deliv_count} deliverable(s)** awaiting your review")

    briefing_text = "\n".join(sections)

    # Save as notification
    notif_id = _create_notification(user_id, {
        "title": f"Daily Briefing — {now.strftime('%b %d')}",
        "body": briefing_text,
        "type": "briefing",
        "priority": "high",
        "agent_id": "jumbo",
        "action_url": "/mission-control",
    }, sb)

    return {
        "briefing": briefing_text,
        "notification_id": notif_id,
        "brand": brand_name,
    }
