"""Orchestrator API: autonomous task scheduling and execution endpoints.

Endpoints:
  POST /orchestrator/pulse     — Evaluate schedules, create & optionally execute tasks
  POST /orchestrator/trigger   — Manually trigger a specific schedule
  POST /orchestrator/execute/{task_id} — Execute a specific orchestrator task
  GET  /orchestrator/status    — Schedules, active tasks, recent history
  GET  /orchestrator/schedules — List schedule definitions

Note: pulse/trigger/execute are declared as sync `def` (not `async def`) so
FastAPI runs them in a thread pool, preventing event-loop starvation during
long-running LLM pipelines.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Path

from app.auth import get_current_user, CurrentUser
from app.schemas.orchestrator import (
    PulseRequest,
    PulseResult,
    TriggerRequest,
    TriggerResult,
    ExecuteResult,
    OrchestratorStatus,
)
from app.services.agent_orchestrator import (
    pulse,
    execute_task,
    trigger_schedule,
    get_status,
    SCHEDULES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


@router.post("/pulse", response_model=PulseResult)
def orchestrator_pulse(
    body: PulseRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Run the orchestrator pulse: check schedules, create & execute due tasks."""
    return pulse(user.id, auto_execute=body.auto_execute, force=body.force)


@router.post("/trigger", response_model=TriggerResult)
def orchestrator_trigger(
    body: TriggerRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Manually trigger a specific schedule, ignoring cooldown."""
    try:
        return trigger_schedule(
            user.id, body.schedule_id, auto_execute=body.auto_execute,
        )
    except ValueError:
        raise HTTPException(400, "Invalid schedule or no active brand")


@router.post("/execute/{task_id}", response_model=ExecuteResult)
def orchestrator_execute(
    task_id: str = Path(..., max_length=80),
    user: CurrentUser = Depends(get_current_user),
):
    """Execute a specific orchestrator task."""
    if not _TASK_ID_RE.match(task_id):
        raise HTTPException(400, "Invalid task ID format")
    try:
        result = execute_task(task_id, user.id)
        return ExecuteResult(
            status=result.get("status", "unknown"),
            task_id=task_id,
            deliverable_id=result.get("deliverable_id"),
            error=result.get("error"),
            details=result,
        )
    except ValueError:
        raise HTTPException(400, "Task not found or cannot be executed")


@router.get("/status", response_model=OrchestratorStatus)
def orchestrator_status(
    user: CurrentUser = Depends(get_current_user),
):
    """Get orchestrator status: schedules, active tasks, recent history."""
    return get_status(user.id)


@router.get("/schedules")
def list_schedules(user: CurrentUser = Depends(get_current_user)):
    """List all schedule definitions."""
    return {
        "schedules": [
            {
                "id": s["id"],
                "name": s["name"],
                "agent_id": s["agent_id"],
                "task_type": s["task_type"],
                "priority": s["priority"],
                "day_of_week": s["day_of_week"],
                "hour": s["hour"],
            }
            for s in SCHEDULES
        ]
    }
