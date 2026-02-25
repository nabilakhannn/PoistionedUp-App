"""Workflow endpoints: create, list, get, topic selection, hook selection, approve/reject, export, inline execute."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.services.analytics import track_event
from app.schemas.workflow import (
    VALID_PLATFORMS,
    ContentAsset,
    WorkflowCreate,
    WorkflowCreated,
    WorkflowDetail,
    WorkflowSummary,
)

logger = logging.getLogger("app.routers.workflows")

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ── Resume request models ────────────────────────────────────


class TopicSelectionRequest(BaseModel):
    """POST /workflows/{id}/topic — user picks a topic candidate."""
    selected_topic_id: str = Field(..., min_length=1)


class HookSelectionRequest(BaseModel):
    """POST /workflows/{id}/hook — user picks a hook candidate."""
    selected_hook_id: str = Field(..., min_length=1)


class ApprovalRequest(BaseModel):
    """POST /workflows/{id}/approve — user approves or rejects."""
    decision: str = Field(..., pattern="^(approved|rejected)$")
    feedback: str = Field(default="")
    regen_from_step: str = Field(default="")


class ResumeResponse(BaseModel):
    """Response after submitting a selection or approval."""
    id: str
    status: str
    message: str


# ── Existing endpoints ───────────────────────────────────────


@router.post("", response_model=WorkflowCreated, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new workflow. Validates brand completeness, captures profile snapshot."""
    admin = get_admin_client()

    # ── Validate platforms ──
    invalid = [p for p in body.platforms if p not in VALID_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid platforms: {invalid}. Valid: {VALID_PLATFORMS}",
        )
    if not body.platforms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one platform is required.",
        )

    # ── Daily workflow cap ──
    from app.routers.usage import check_daily_workflow_cap

    cap_info = check_daily_workflow_cap(user.id)
    if cap_info["at_limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily workflow limit reached ({cap_info['cap']} per day). "
                "Try again tomorrow or contact support to increase your limit."
            ),
        )

    # ── Resolve brand_id ──
    brand_id = body.brand_id

    if not brand_id:
        # Fallback: find the user's first active personal brand
        default_resp = (
            admin.table("personal_brands")
            .select("id")
            .eq("user_id", user.id)
            .eq("is_active", True)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        if default_resp.data:
            brand_id = default_resp.data[0]["id"]

    # ── Brand completeness gate ──
    profile_snapshot = {}

    model_tier = ""
    if brand_id:
        # Fetch profile from the personal_brands table
        brand_resp = (
            admin.table("personal_brands")
            .select("profile_json, model_tier")
            .eq("id", brand_id)
            .eq("user_id", user.id)
            .execute()
        )
        if not brand_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal brand not found.",
            )
        profile_snapshot = brand_resp.data[0].get("profile_json", {}) or {}
        model_tier = brand_resp.data[0].get("model_tier", "") or ""
    else:
        # Legacy fallback: read from profiles table
        legacy_resp = (
            admin.table("profiles")
            .select("profile_json")
            .eq("user_id", user.id)
            .execute()
        )
        profile_snapshot = (
            legacy_resp.data[0].get("profile_json", {}) if legacy_resp.data else {}
        )

    # Calculate completeness: require at least 50% of brand profile done
    from app.services.brand_chat import calculate_completeness

    completeness = calculate_completeness(profile_snapshot)
    completeness_pct = completeness["overall_percent"]
    if completeness_pct < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Brand profile is only {completeness_pct}% complete. "
                "Complete at least 4 of 8 brand modules before creating content. "
                "Go to /brands to fill them in."
            ),
        )

    # Merge platforms into settings
    merged_settings = dict(body.settings)
    merged_settings["platforms"] = body.platforms
    if model_tier:
        merged_settings["model_tier"] = model_tier

    # Build workflow insert data
    wf_data = {
        "user_id": user.id,
        "status": "queued",
        "goal_text": body.goal_text,
        "settings": merged_settings,
        "profile_snapshot": profile_snapshot,
    }
    if brand_id:
        wf_data["brand_id"] = brand_id

    # Insert workflow row
    wf_resp = (
        admin.table("workflows")
        .insert(wf_data)
        .execute()
    )

    wf = wf_resp.data[0]

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": wf["id"],
        "event_type": "workflow_created",
        "payload": {
            "goal_text": body.goal_text,
            "platforms": body.platforms,
            "brand_id": brand_id,
        },
    }).execute()

    # Track workflow creation in PostHog
    track_event(user.id, "workflow_created", {
        "workflow_id": wf["id"],
        "goal_text": body.goal_text[:100],
        "platforms": body.platforms,
        "brand_id": brand_id or "",
        "objective": merged_settings.get("objective", ""),
        "content_type": merged_settings.get("content_type", ""),
    })

    # No explicit enqueue needed: worker polls for status=queued rows
    return WorkflowCreated(id=wf["id"], status=wf["status"])


# ── Inline Pipeline Execution (serverless-compatible) ─────


@router.post("/{workflow_id}/execute")
async def execute_workflow_inline(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Execute the pipeline inline within this API request.

    Works on Vercel without a separate worker process. Runs the pipeline
    until it hits an interrupt point (topic selection, hook lab, approval)
    or completes. Each segment fits within Vercel's 120-second timeout.

    For resume support across serverless invocations, set LANGGRAPH_DB_URI
    to a direct Postgres connection string (e.g., Supabase direct URL).
    Without it, MemorySaver is used (only works within the same process).
    """
    admin = get_admin_client()

    # Verify ownership and get current state
    resp = (
        admin.table("workflows")
        .select("id, status, settings, current_step, user_id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    wf = resp.data[0]
    current_status = wf["status"]
    wf_settings = wf.get("settings", {}) or {}
    resume_payload = wf_settings.get("_resume")

    if current_status != "queued":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot execute: workflow status is '{current_status}', "
                "expected 'queued'. The pipeline may already be running."
            ),
        )

    # Atomically claim the workflow (prevents worker race condition)
    now = datetime.now(timezone.utc).isoformat()
    claim_resp = (
        admin.table("workflows")
        .update({
            "status": "running",
            "current_step": wf.get("current_step") or "signal_research",
            "claimed_at": now,
        })
        .eq("id", workflow_id)
        .eq("status", "queued")  # Optimistic lock
        .execute()
    )

    if not claim_resp.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow was already claimed by another process.",
        )

    # Determine action: fresh run or resume from interrupt
    action = "resume" if resume_payload else "run"

    # Run pipeline in a thread pool (graph.invoke is synchronous)
    from worker.executor import run_pipeline

    try:
        final_status = await asyncio.to_thread(
            run_pipeline,
            client=admin,
            workflow_id=workflow_id,
            action=action,
            resume_payload=resume_payload,
        )
    except Exception as e:
        logger.exception(
            "Inline pipeline execution failed for workflow %s", workflow_id
        )
        try:
            admin.table("workflows").update({
                "status": "failed",
                "error_message": str(e)[:500],
                "claimed_at": None,
            }).eq("id", workflow_id).execute()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)[:200]}",
        )

    # Clean up: clear claimed_at and resume payload
    clean_data: Dict[str, Any] = {"claimed_at": None}
    if resume_payload:
        clean_settings = {
            k: v for k, v in wf_settings.items() if k != "_resume"
        }
        clean_data["settings"] = clean_settings
    admin.table("workflows").update(clean_data).eq("id", workflow_id).execute()

    # Return updated workflow status
    updated = (
        admin.table("workflows")
        .select("id, status, current_step, error_message")
        .eq("id", workflow_id)
        .execute()
    )
    return updated.data[0] if updated.data else {
        "id": workflow_id,
        "status": final_status,
    }


@router.get("", response_model=List[WorkflowSummary])
async def list_workflows(
    brand_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List all workflows for the authenticated user, newest first.
    Pass ?brand_id= to filter by personal brand.
    """
    admin = get_admin_client()

    query = (
        admin.table("workflows")
        .select("id, status, goal_text, current_step, active_version, settings, created_at, updated_at")
        .eq("user_id", user.id)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.order("created_at", desc=True).execute()

    # Fetch cost totals per workflow in a single query
    wf_ids = [row["id"] for row in resp.data]
    cost_map = {}  # type: Dict[str, float]
    if wf_ids:
        cost_resp = (
            admin.table("usage_costs")
            .select("workflow_id, estimated_cost")
            .eq("user_id", user.id)
            .in_("workflow_id", wf_ids)
            .execute()
        )
        for row_cost in (cost_resp.data or []):
            wid = row_cost["workflow_id"]
            cost_map[wid] = cost_map.get(wid, 0.0) + float(row_cost.get("estimated_cost", 0))

    results = []
    for row in resp.data:
        s = row.get("settings") or {}
        platforms = s.get("platforms", ["youtube"])
        results.append(WorkflowSummary(
            id=row["id"],
            status=row["status"],
            goal_text=row["goal_text"],
            current_step=row.get("current_step"),
            active_version=row["active_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            platforms=platforms,
            estimated_cost=round(cost_map.get(row["id"], 0.0), 6),
            objective=s.get("objective"),
            content_type=s.get("content_type"),
        ))
    return results


@router.get("/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single workflow by ID. Returns 404 if not found or not owned by user."""
    admin = get_admin_client()

    resp = (
        admin.table("workflows")
        .select("*")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    row = resp.data[0]
    platforms = (row.get("settings") or {}).get("platforms", ["youtube"])
    return WorkflowDetail(**row, platforms=platforms)


@router.get("/{workflow_id}/assets", response_model=List[ContentAsset])
async def get_workflow_assets(
    workflow_id: str,
    all_versions: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    """Fetch content_assets for a given workflow (latest versions by default)."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    query = (
        admin.table("content_assets")
        .select("*")
        .eq("workflow_id", workflow_id)
    )
    if not all_versions:
        query = query.eq("is_latest", True)

    resp = query.order("created_at", desc=False).execute()

    return [ContentAsset(**row) for row in (resp.data or [])]


# ── Asset endpoints ───────────────────────────────────────────


class AssetUpdateRequest(BaseModel):
    """PATCH /workflows/{id}/assets/{asset_id} request body."""
    title: str = None
    body: Dict[str, Any] = None


@router.patch("/{workflow_id}/assets/{asset_id}", response_model=Dict[str, Any])
async def update_workflow_asset(
    workflow_id: str,
    asset_id: str,
    body: AssetUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Inline edit a content asset. Creates a new version, preserving the old one."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Fetch the current asset
    old_resp = (
        admin.table("content_assets")
        .select("*")
        .eq("id", asset_id)
        .eq("workflow_id", workflow_id)
        .execute()
    )
    if not old_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    old_asset = old_resp.data[0]
    old_version = old_asset.get("version", 1)

    # Build new content_json
    new_content_json = dict(old_asset.get("content_json", {}))
    if body.body is not None:
        new_content_json.update(body.body)

    has_changes = body.title is not None or body.body is not None
    if not has_changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nothing to update",
        )

    # Mark old asset as not latest
    admin.table("content_assets").update({
        "is_latest": False,
    }).eq("id", asset_id).execute()

    # Create new version
    new_row = {
        "workflow_id": workflow_id,
        "type": old_asset["type"],
        "platform": old_asset.get("platform", "youtube"),
        "content_json": new_content_json,
        "version": old_version + 1,
        "status": old_asset.get("status", "draft"),
        "is_latest": True,
    }
    new_resp = admin.table("content_assets").insert(new_row).execute()

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": "asset_edited",
        "payload": {
            "old_asset_id": asset_id,
            "new_asset_id": new_resp.data[0]["id"] if new_resp.data else None,
            "old_version": old_version,
            "new_version": old_version + 1,
        },
    }).execute()

    return new_resp.data[0] if new_resp.data else old_asset


@router.get("/{workflow_id}/assets/{asset_id}/versions", response_model=List[ContentAsset])
async def get_asset_versions(
    workflow_id: str,
    asset_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get all versions of a content asset (including previous edits)."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Get the target asset to find its type
    asset_resp = (
        admin.table("content_assets")
        .select("type, platform")
        .eq("id", asset_id)
        .eq("workflow_id", workflow_id)
        .execute()
    )
    if not asset_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    asset_type = asset_resp.data[0]["type"]
    platform = asset_resp.data[0].get("platform", "youtube")

    # Find all versions of this asset type for this workflow
    resp = (
        admin.table("content_assets")
        .select("*")
        .eq("workflow_id", workflow_id)
        .eq("type", asset_type)
        .eq("platform", platform)
        .order("version", desc=True)
        .execute()
    )

    return [ContentAsset(**row) for row in (resp.data or [])]


@router.post("/{workflow_id}/assets/{asset_id}/restore", response_model=Dict[str, Any])
async def restore_asset_version(
    workflow_id: str,
    asset_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Restore an older version of an asset, making it the latest."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    # Get the asset to restore
    asset_resp = (
        admin.table("content_assets")
        .select("*")
        .eq("id", asset_id)
        .eq("workflow_id", workflow_id)
        .execute()
    )
    if not asset_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    old_asset = asset_resp.data[0]

    # Find current latest version for this type
    latest_resp = (
        admin.table("content_assets")
        .select("id, version")
        .eq("workflow_id", workflow_id)
        .eq("type", old_asset["type"])
        .eq("platform", old_asset.get("platform", "youtube"))
        .eq("is_latest", True)
        .execute()
    )
    max_version = max((r["version"] for r in latest_resp.data), default=1) if latest_resp.data else 1

    # Mark current latest as not latest
    for row in (latest_resp.data or []):
        admin.table("content_assets").update({
            "is_latest": False,
        }).eq("id", row["id"]).execute()

    # Create a new row that's a copy of the old version, with bumped version number
    new_row = {
        "workflow_id": workflow_id,
        "type": old_asset["type"],
        "platform": old_asset.get("platform", "youtube"),
        "content_json": old_asset["content_json"],
        "version": max_version + 1,
        "status": old_asset.get("status", "draft"),
        "is_latest": True,
        "feedback": f"Restored from version {old_asset['version']}",
    }
    new_resp = admin.table("content_assets").insert(new_row).execute()

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": "asset_version_restored",
        "payload": {
            "restored_from_id": asset_id,
            "restored_from_version": old_asset["version"],
            "new_version": max_version + 1,
        },
    }).execute()

    return new_resp.data[0] if new_resp.data else old_asset


# ── Snapshot endpoints ────────────────────────────────────────


@router.get("/{workflow_id}/snapshots")
async def get_workflow_snapshots(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Fetch all pipeline step snapshots for a workflow, ordered by creation time."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    snap_resp = (
        admin.table("workflow_snapshots")
        .select("id, step_id, version, state_json, created_at")
        .eq("workflow_id", workflow_id)
        .order("created_at", desc=False)
        .execute()
    )

    # Return a simplified summary per step (avoid sending huge state_json)
    snapshots = []
    for snap in (snap_resp.data or []):
        state = snap.get("state_json") or {}
        # Extract a human-readable summary for each step
        summary = _summarize_snapshot(snap["step_id"], state)
        snapshots.append({
            "id": snap["id"],
            "step_id": snap["step_id"],
            "version": snap["version"],
            "created_at": snap["created_at"],
            "summary": summary,
        })

    return {"snapshots": snapshots}


def _summarize_snapshot(step_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a concise summary from a snapshot's state_json for UI display."""
    summary: Dict[str, Any] = {}

    if step_id == "signal_research":
        signals = state.get("signals", [])
        summary["signal_count"] = len(signals)
        summary["sources"] = list(set(
            s.get("source", "unknown") for s in signals[:20]
        ))
        summary["top_signals"] = [
            s.get("title", s.get("headline", ""))[:80]
            for s in signals[:5]
        ]

    elif step_id == "gap_analysis":
        topics = state.get("topic_candidates", [])
        summary["topic_count"] = len(topics)
        summary["top_topics"] = [
            {"title": t.get("title", "")[:80], "score": t.get("opportunity_score", 0)}
            for t in sorted(topics, key=lambda x: x.get("opportunity_score", 0), reverse=True)[:5]
        ]

    elif step_id == "topic_selection":
        selected = state.get("selected_topic")
        if isinstance(selected, dict):
            summary["selected_topic"] = selected.get("title", "")
        elif isinstance(selected, str):
            summary["selected_topic"] = selected

    elif step_id == "hook_lab":
        hooks = state.get("hook_candidates", [])
        summary["hook_count"] = len(hooks)
        summary["hooks"] = [
            {"text": h.get("hook_text", "")[:100], "score": h.get("total_score", 0), "type": h.get("hook_type", "")}
            for h in sorted(hooks, key=lambda x: x.get("total_score", 0), reverse=True)[:5]
        ]

    elif step_id == "script_generation":
        pack = state.get("content_pack", {})
        summary["has_youtube_long"] = bool(pack.get("youtube_long"))
        summary["youtube_shorts_count"] = len(pack.get("youtube_shorts", []))
        summary["linkedin_posts_count"] = len(pack.get("linkedin_posts", []))
        summary["twitter_posts_count"] = len(pack.get("twitter_posts", []))
        summary["word_count"] = pack.get("youtube_long", {}).get("word_count", 0)

    elif step_id == "editor":
        edited = state.get("edited_pack", {})
        summary["edited"] = bool(edited)
        summary["word_count"] = edited.get("youtube_long", {}).get("word_count", 0)

    elif step_id == "testing":
        report = state.get("test_report", {})
        summary["passed"] = report.get("overall_pass", False)
        summary["checks_passed"] = report.get("checks_passed", 0)
        summary["checks_total"] = report.get("checks_total", 0)
        summary["flags"] = report.get("flags", [])[:5]

    elif step_id == "approval":
        summary["status"] = state.get("approval_status", "pending")

    return summary


# ── Data endpoints (topics, hooks) ────────────────────────────


@router.get("/{workflow_id}/topics")
async def get_workflow_topics(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Fetch topic candidates from workflow snapshots."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id, settings")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Look for topic_selection or gap_analysis snapshot
    snap_resp = (
        admin.table("workflow_snapshots")
        .select("state_json")
        .eq("workflow_id", workflow_id)
        .in_("step_id", ["gap_analysis", "topic_selection"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if snap_resp.data:
        state = snap_resp.data[0].get("state_json", {})
        topics = state.get("topic_candidates", [])
    else:
        # Also check workflow settings for stored topics
        settings = wf_resp.data[0].get("settings", {})
        topics = settings.get("_topics", [])

    return {"topics": topics}


@router.get("/{workflow_id}/hooks")
async def get_workflow_hooks(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Fetch hook candidates from workflow snapshots."""
    admin = get_admin_client()

    # Verify ownership
    wf_resp = (
        admin.table("workflows")
        .select("id, settings")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Look for hook_lab snapshot
    snap_resp = (
        admin.table("workflow_snapshots")
        .select("state_json")
        .eq("workflow_id", workflow_id)
        .eq("step_id", "hook_lab")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if snap_resp.data:
        state = snap_resp.data[0].get("state_json", {})
        hooks = state.get("hook_candidates", [])
        selected_topic = state.get("selected_topic", None)
    else:
        settings = wf_resp.data[0].get("settings", {})
        hooks = settings.get("_hooks", [])
        selected_topic = settings.get("_selected_topic", None)

    return {"hooks": hooks, "selected_topic": selected_topic}


# ── Export endpoints ─────────────────────────────────────────


def _get_content_pack(admin, workflow_id: str, user_id: str) -> Dict[str, Any]:
    """Retrieve the content pack from the latest snapshot or settings."""
    wf_resp = (
        admin.table("workflows")
        .select("id, settings, status")
        .eq("id", workflow_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not wf_resp.data:
        raise HTTPException(status_code=404, detail="Workflow not found")

    settings = wf_resp.data[0].get("settings", {})

    # Try snapshots first
    snap_resp = (
        admin.table("workflow_snapshots")
        .select("state_json")
        .eq("workflow_id", workflow_id)
        .in_("step_id", ["editor", "testing", "approval"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if snap_resp.data:
        state = snap_resp.data[0].get("state_json", {})
        pack = state.get("edited_pack") or state.get("content_pack", {})
        if pack:
            return pack

    # Fallback to settings
    return settings.get("_edited_pack") or settings.get("_content_pack", {})


def _format_content_as_text(pack: Dict[str, Any]) -> str:
    """Format content pack as readable plain text for clipboard/markdown."""
    lines = []

    # YouTube
    yt_long = pack.get("youtube_long", {})
    if yt_long:
        lines.append("=" * 60)
        lines.append("YOUTUBE LONG-FORM SCRIPT")
        lines.append("=" * 60)
        if yt_long.get("hook"):
            lines.append("\n[HOOK]")
            lines.append(yt_long["hook"])
        for section in yt_long.get("sections", []):
            lines.append("\n---")
            ts = section.get("timestamp", "")
            lines.append(f"[{ts}] {section.get('heading', '')}")
            lines.append(section.get("script", ""))

    titles = pack.get("titles", [])
    if titles:
        lines.append("\n\nTITLE OPTIONS:")
        for i, t in enumerate(titles, 1):
            lines.append(f"  {i}. {t}")

    desc = pack.get("description", "")
    if desc:
        lines.append("\n\nDESCRIPTION:")
        lines.append(desc)

    tags = pack.get("tags", [])
    if tags:
        lines.append("\n\nTAGS: " + ", ".join(tags))

    pinned = pack.get("pinned_comment", "")
    if pinned:
        lines.append("\n\nPINNED COMMENT:")
        lines.append(pinned)

    # YouTube Shorts
    shorts = pack.get("youtube_shorts", [])
    if shorts:
        lines.append("\n\n" + "=" * 60)
        lines.append("YOUTUBE SHORTS")
        lines.append("=" * 60)
        for i, s in enumerate(shorts, 1):
            lines.append(f"\n--- Short #{i} ---")
            lines.append(f"Hook: {s.get('hook', '')}")
            lines.append(s.get("script", ""))
            if s.get("cta"):
                lines.append(f"CTA: {s['cta']}")

    # LinkedIn
    li_posts = pack.get("linkedin_posts", [])
    if li_posts:
        lines.append("\n\n" + "=" * 60)
        lines.append("LINKEDIN POSTS")
        lines.append("=" * 60)
        for i, p in enumerate(li_posts, 1):
            lines.append(f"\n--- Post #{i} ({p.get('post_type', 'post')}) ---")
            if p.get("hook_line"):
                lines.append(p["hook_line"])
                lines.append("")
            lines.append(p.get("body", ""))
            if p.get("cta"):
                lines.append(f"\n{p['cta']}")

    # Twitter
    tw_posts = pack.get("twitter_posts", [])
    if tw_posts:
        lines.append("\n\n" + "=" * 60)
        lines.append("TWITTER/X POSTS")
        lines.append("=" * 60)
        for i, t in enumerate(tw_posts, 1):
            lines.append(f"\n--- Tweet #{i} ({t.get('angle', '')}) ---")
            lines.append(t.get("tweet_text", ""))

    tw_thread = pack.get("twitter_thread", {})
    if tw_thread and tw_thread.get("hook_tweet"):
        lines.append(f"\n--- Thread ---")
        lines.append(f"1/ {tw_thread['hook_tweet']}")
        for j, tweet in enumerate(tw_thread.get("tweets", []), 2):
            lines.append(f"{j}/ {tweet}")

    # Short-form
    sf_scripts = pack.get("short_form_scripts", [])
    if sf_scripts:
        lines.append("\n\n" + "=" * 60)
        lines.append("SHORT-FORM SCRIPTS (TikTok/Reels/Shorts)")
        lines.append("=" * 60)
        for i, s in enumerate(sf_scripts, 1):
            lines.append(f"\n--- Script #{i} ({s.get('angle', '')}) ---")
            lines.append(f"Hook: {s.get('hook', '')}")
            lines.append(s.get("script", ""))
            if s.get("punchline"):
                lines.append(f"Punchline: {s['punchline']}")
            if s.get("cta"):
                lines.append(f"CTA: {s['cta']}")

    return "\n".join(lines)


def _format_content_as_markdown(pack: Dict[str, Any], goal_text: str = "") -> str:
    """Format content pack as Markdown."""
    lines = []
    lines.append(f"# Content Pack{': ' + goal_text if goal_text else ''}")
    lines.append("")

    # YouTube
    yt_long = pack.get("youtube_long", {})
    if yt_long:
        lines.append("## YouTube Long-Form Script")
        lines.append("")
        if yt_long.get("hook"):
            lines.append("### Hook")
            lines.append(yt_long["hook"])
            lines.append("")
        for section in yt_long.get("sections", []):
            ts = section.get("timestamp", "")
            heading = section.get("heading", "")
            lines.append(f"### [{ts}] {heading}")
            lines.append(section.get("script", ""))
            if section.get("broll_suggestion"):
                lines.append(f"\n> B-roll: {section['broll_suggestion']}")
            lines.append("")

    titles = pack.get("titles", [])
    if titles:
        lines.append("### Title Options")
        for i, t in enumerate(titles, 1):
            lines.append(f"{i}. {t}")
        lines.append("")

    desc = pack.get("description", "")
    if desc:
        lines.append("### Description")
        lines.append(desc)
        lines.append("")

    tags = pack.get("tags", [])
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}")
        lines.append("")

    # YouTube Shorts
    shorts = pack.get("youtube_shorts", [])
    if shorts:
        lines.append("## YouTube Shorts")
        lines.append("")
        for i, s in enumerate(shorts, 1):
            lines.append(f"### Short #{i}")
            lines.append(f"**Hook:** {s.get('hook', '')}")
            lines.append("")
            lines.append(s.get("script", ""))
            if s.get("cta"):
                lines.append(f"\n**CTA:** {s['cta']}")
            lines.append("")

    # LinkedIn
    li_posts = pack.get("linkedin_posts", [])
    if li_posts:
        lines.append("## LinkedIn Posts")
        lines.append("")
        for i, p in enumerate(li_posts, 1):
            ptype = p.get("post_type", "post").title()
            lines.append(f"### Post #{i} ({ptype})")
            if p.get("hook_line"):
                lines.append(f"**{p['hook_line']}**")
                lines.append("")
            lines.append(p.get("body", ""))
            if p.get("cta"):
                lines.append(f"\n*{p['cta']}*")
            lines.append("")

    # Twitter
    tw_posts = pack.get("twitter_posts", [])
    if tw_posts:
        lines.append("## Twitter/X Posts")
        lines.append("")
        for i, t in enumerate(tw_posts, 1):
            lines.append(f"### Tweet #{i} ({t.get('angle', '')})")
            lines.append(f"> {t.get('tweet_text', '')}")
            lines.append("")

    tw_thread = pack.get("twitter_thread", {})
    if tw_thread and tw_thread.get("hook_tweet"):
        lines.append("### Thread")
        lines.append(f"**1/** {tw_thread['hook_tweet']}")
        lines.append("")
        for j, tweet in enumerate(tw_thread.get("tweets", []), 2):
            lines.append(f"**{j}/** {tweet}")
            lines.append("")

    # Short-form
    sf_scripts = pack.get("short_form_scripts", [])
    if sf_scripts:
        lines.append("## Short-Form Scripts")
        lines.append("")
        for i, s in enumerate(sf_scripts, 1):
            angle = s.get("angle", "").replace("_", " ").title()
            lines.append(f"### Script #{i} ({angle})")
            lines.append(f"**Hook:** {s.get('hook', '')}")
            lines.append("")
            lines.append(s.get("script", ""))
            if s.get("punchline"):
                lines.append(f"\n**Punchline:** {s['punchline']}")
            if s.get("cta"):
                lines.append(f"**CTA:** {s['cta']}")
            lines.append("")

    return "\n".join(lines)


@router.post("/{workflow_id}/export/clipboard")
async def export_clipboard(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return formatted plain text for all content (clipboard copy)."""
    admin = get_admin_client()
    pack = _get_content_pack(admin, workflow_id, user.id)
    text = _format_content_as_text(pack)
    return {"text": text, "format": "plain_text"}


@router.post("/{workflow_id}/export/google-docs")
async def export_google_docs(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Export content pack as a formatted Google Doc. Requires Google OAuth connection."""
    from app.routers.oauth import get_google_credentials
    from app.services.google_docs import create_google_doc

    creds = get_google_credentials(user.id)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google account not connected. Go to Settings to connect Google.",
        )

    admin = get_admin_client()

    # Get goal text
    wf_resp = (
        admin.table("workflows")
        .select("goal_text")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    goal_text = wf_resp.data[0]["goal_text"] if wf_resp.data else ""

    pack = _get_content_pack(admin, workflow_id, user.id)

    try:
        doc_url = create_google_doc(creds, pack, goal_text=goal_text)
    except Exception as e:
        logger.error("Google Docs export failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Google Doc. Try reconnecting your Google account.",
        )

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": "exported",
        "payload": {"format": "google_docs", "url": doc_url},
    }).execute()

    return {"url": doc_url, "format": "google_docs"}


@router.post("/{workflow_id}/export/notion")
async def export_notion(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Export content pack as a formatted Notion page. Requires Notion OAuth connection."""
    from app.routers.oauth import get_notion_token
    from app.services.notion_export import create_notion_page

    token = get_notion_token(user.id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Notion account not connected. Go to Settings to connect Notion.",
        )

    admin = get_admin_client()

    # Get goal text
    wf_resp = (
        admin.table("workflows")
        .select("goal_text")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    goal_text = wf_resp.data[0]["goal_text"] if wf_resp.data else ""

    pack = _get_content_pack(admin, workflow_id, user.id)

    try:
        page_url = await create_notion_page(token, pack, goal_text=goal_text)
    except Exception as e:
        logger.error("Notion export failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Notion page. Try reconnecting your Notion account.",
        )

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": "exported",
        "payload": {"format": "notion", "url": page_url},
    }).execute()

    return {"url": page_url, "format": "notion"}


@router.post("/{workflow_id}/export/markdown")
async def export_markdown(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return Markdown-formatted content."""
    admin = get_admin_client()

    # Get goal text for the title
    wf_resp = (
        admin.table("workflows")
        .select("goal_text")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )
    goal_text = wf_resp.data[0]["goal_text"] if wf_resp.data else ""

    pack = _get_content_pack(admin, workflow_id, user.id)
    md = _format_content_as_markdown(pack, goal_text=goal_text)

    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="content-{workflow_id[:8]}.md"'},
    )


# ── Abandon endpoint ──────────────────────────────────────────


@router.post("/{workflow_id}/abandon", response_model=ResumeResponse)
async def abandon_workflow(
    workflow_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Abandon a workflow. Marks it as failed with user-initiated reason.

    Can be called on any active workflow (queued, running, awaiting_*).
    """
    admin = get_admin_client()

    resp = (
        admin.table("workflows")
        .select("id, status")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    wf = resp.data[0]
    terminal_statuses = {"approved", "rejected", "failed"}

    if wf["status"] in terminal_statuses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow is already in terminal status '{wf['status']}'",
        )

    admin.table("workflows").update({
        "status": "failed",
        "error_message": "Abandoned by user",
        "claimed_at": None,
    }).eq("id", workflow_id).execute()

    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": "failed",
        "payload": {"reason": "user_abandoned"},
    }).execute()

    return ResumeResponse(
        id=workflow_id,
        status="failed",
        message="Workflow abandoned.",
    )


# ── Resume endpoints ─────────────────────────────────────────


@router.post("/{workflow_id}/topic", response_model=ResumeResponse)
async def select_topic(
    workflow_id: str,
    body: TopicSelectionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit a topic selection to resume the pipeline."""
    return await _resume_workflow(
        workflow_id=workflow_id,
        user=user,
        expected_status="awaiting_topic",
        resume_payload={"selected_topic_id": body.selected_topic_id},
        event_type="topic_selected",
    )


@router.post("/{workflow_id}/hook", response_model=ResumeResponse)
async def select_hook(
    workflow_id: str,
    body: HookSelectionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit a hook selection to resume the pipeline."""
    return await _resume_workflow(
        workflow_id=workflow_id,
        user=user,
        expected_status="awaiting_hook",
        resume_payload={"selected_hook_id": body.selected_hook_id},
        event_type="hook_selected",
    )


@router.post("/{workflow_id}/approve", response_model=ResumeResponse)
async def approve_workflow(
    workflow_id: str,
    body: ApprovalRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit an approval decision to resume the pipeline."""
    return await _resume_workflow(
        workflow_id=workflow_id,
        user=user,
        expected_status="awaiting_approval",
        resume_payload={
            "decision": body.decision,
            "feedback": body.feedback,
        },
        event_type=body.decision,
    )


async def _resume_workflow(
    workflow_id: str,
    user: CurrentUser,
    expected_status: str,
    resume_payload: Dict[str, Any],
    event_type: str,
) -> ResumeResponse:
    """Common logic for resume endpoints: validate, store payload, re-queue."""
    admin = get_admin_client()

    # Verify workflow exists and belongs to user
    resp = (
        admin.table("workflows")
        .select("id, status, settings, user_id")
        .eq("id", workflow_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    wf = resp.data[0]

    if wf["status"] != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow status is '{wf['status']}', expected '{expected_status}'",
        )

    # Store resume payload in settings._resume and re-queue
    updated_settings = dict(wf.get("settings", {}) or {})
    updated_settings["_resume"] = resume_payload

    admin.table("workflows").update({
        "settings": updated_settings,
        "status": "queued",
    }).eq("id", workflow_id).execute()

    # Log audit event
    admin.table("audit_events").insert({
        "user_id": user.id,
        "workflow_id": workflow_id,
        "event_type": event_type,
        "payload": resume_payload,
    }).execute()

    # Track resume events in PostHog
    track_event(user.id, f"workflow_{event_type}", {
        "workflow_id": workflow_id,
        **resume_payload,
    })

    return ResumeResponse(
        id=workflow_id,
        status="queued",
        message="Selection received. Pipeline will resume shortly.",
    )
