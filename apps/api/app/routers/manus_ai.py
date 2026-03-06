"""Manus AI Router — Slice 109.

Optional BYOK endpoints for Manus AI integration.
Only used when user has configured their Manus API key.

Endpoints (all JWT-protected):
  POST /manus/task          — Create a Manus task
  GET  /manus/task/{id}     — Poll task status
  POST /agent-api/webhooks/manus — Webhook receiver for Manus callbacks
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.manus_ai")

router = APIRouter(tags=["manus-ai"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ── Schemas ────────────────────────────────────────────────────────────────


class CreateTaskRequest(BaseModel):
    brand_id: str
    workflow_slug: str
    prompt: str = Field(..., min_length=1)
    mode: str = Field(default="agent")
    profile: str = Field(default="quality")


class TaskStatusResponse(BaseModel):
    id: str
    manus_task_id: Optional[str] = None
    workflow_slug: str
    status: str
    result_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/manus/task", response_model=TaskStatusResponse, status_code=201)
async def create_manus_task(
    body: CreateTaskRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new Manus AI task.

    Requires user to have a Manus API key configured in connectors.
    """
    if not _UUID_RE.match(body.brand_id):
        raise HTTPException(400, "Invalid brand_id")

    from app.services.manus_ai import (
        ManusAIClient,
        get_manus_api_key,
        save_manus_task,
    )

    # Get user's Manus API key
    api_key = get_manus_api_key(user.id)
    if not api_key:
        raise HTTPException(
            400,
            "Manus AI API key not configured. Add it in Brand → Settings → Connectors.",
        )

    # Create task via Manus API
    client = ManusAIClient(api_key)
    try:
        result = await client.create_task(
            prompt=body.prompt,
            mode=body.mode,
            profile=body.profile,
        )
    except Exception as exc:
        logger.error("Manus task creation failed: %s", str(exc)[:200])
        raise HTTPException(502, f"Manus AI error: {str(exc)[:200]}")

    # Save to our database
    internal_id = await save_manus_task(
        user_id=user.id,
        brand_id=body.brand_id,
        workflow_slug=body.workflow_slug,
        manus_task_id=result["task_id"],
        prompt_sent=body.prompt,
    )

    return TaskStatusResponse(
        id=internal_id,
        manus_task_id=result["task_id"],
        workflow_slug=body.workflow_slug,
        status=result["status"],
        created_at="",  # Will be set by DB
    )


@router.get("/manus/task/{task_id}", response_model=TaskStatusResponse)
async def poll_manus_task(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Poll a Manus task for status updates.

    Frontend polls this every 5s until status is completed/failed/timeout.
    """
    if not _UUID_RE.match(task_id):
        raise HTTPException(400, "Invalid task_id")

    from app.services.manus_ai import (
        ManusAIClient,
        get_manus_api_key,
        get_manus_task,
        update_manus_task,
    )

    # Fetch internal task (IDOR guard via user_id)
    task = await get_manus_task(task_id, user.id)
    if not task:
        raise HTTPException(404, "Task not found")

    # If already terminal, return cached result
    if task["status"] in ("completed", "failed", "timeout"):
        return TaskStatusResponse(
            id=task["id"],
            manus_task_id=task.get("manus_task_id"),
            workflow_slug=task["workflow_slug"],
            status=task["status"],
            result_text=task.get("result_text"),
            error_message=task.get("error_message"),
            created_at=str(task.get("created_at", "")),
            completed_at=str(task["completed_at"]) if task.get("completed_at") else None,
        )

    # Poll Manus API for live status
    api_key = get_manus_api_key(user.id)
    if not api_key or not task.get("manus_task_id"):
        raise HTTPException(500, "Cannot poll: missing API key or task ID")

    client = ManusAIClient(api_key)
    try:
        poll_result = await client.poll_task(task["manus_task_id"])
    except Exception as exc:
        logger.warning("Manus poll failed: %s", str(exc)[:200])
        return TaskStatusResponse(
            id=task["id"],
            manus_task_id=task.get("manus_task_id"),
            workflow_slug=task["workflow_slug"],
            status=task["status"],
            created_at=str(task.get("created_at", "")),
        )

    # Update DB if status changed
    new_status = poll_result["status"]
    if new_status != task["status"]:
        await update_manus_task(
            task_id=task_id,
            user_id=user.id,
            status=new_status,
            result_text=poll_result.get("result_text"),
            error_message=poll_result.get("error"),
        )

    return TaskStatusResponse(
        id=task["id"],
        manus_task_id=task.get("manus_task_id"),
        workflow_slug=task["workflow_slug"],
        status=new_status,
        result_text=poll_result.get("result_text"),
        error_message=poll_result.get("error"),
        created_at=str(task.get("created_at", "")),
        completed_at=str(task["completed_at"]) if task.get("completed_at") else None,
    )


@router.post("/agent-api/webhooks/manus")
async def manus_webhook(request: Request):
    """Receive async task completion callbacks from Manus.

    Manus sends: {"task_id": "...", "status": "completed", "result": {...}}
    We update our manus_tasks row accordingly.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    manus_task_id = body.get("task_id")
    if not manus_task_id:
        raise HTTPException(400, "Missing task_id")

    status = body.get("status", "completed")
    result_text = None
    error_message = None

    if status == "completed":
        result_data = body.get("result", {})
        result_text = (
            result_data.get("text")
            or result_data.get("output")
            or str(result_data) if result_data else None
        )
    elif status == "failed":
        error_message = body.get("error", {}).get("message", "Unknown error")

    # Find and update the task by manus_task_id
    sb = get_admin_client()
    from datetime import datetime, timezone

    existing = (
        sb.table("manus_tasks")
        .select("id, user_id")
        .eq("manus_task_id", manus_task_id)
        .limit(1)
        .execute()
    )

    if not existing.data:
        logger.warning("Manus webhook: unknown task_id=%s", manus_task_id)
        return {"ok": False, "reason": "unknown task"}

    task_row = existing.data[0]
    update_data = {
        "status": status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if result_text:
        update_data["result_text"] = result_text
    if error_message:
        update_data["error_message"] = error_message

    sb.table("manus_tasks").update(update_data).eq("id", task_row["id"]).execute()

    logger.info("Manus webhook processed: task=%s status=%s", manus_task_id, status)
    return {"ok": True}
