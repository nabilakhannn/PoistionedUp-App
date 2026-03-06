"""Content Planning Router — Slice 106.

User co-creates a content plan with Jumbo in a conversation, then approves it.
The VPS pipeline runner polls for approved plans and executes them — writing each
approved topic as a separate post (skipping Phase 1 research since topics are explicit).

User endpoints (JWT auth):
  POST /plan/brainstorm        — Jumbo opens the planning conversation with trending opportunities
  POST /plan/chat              — Continue the multi-turn planning conversation
  POST /plan/approve           — User approves the finalised plan; saves to DB
  GET  /plan/status/{plan_id}  — Poll plan execution progress

VPS endpoints (pipeline-key auth):
  GET   /plan/approved-for-runner        — Fetch all approved plans awaiting execution
  PATCH /plan/{plan_id}/status           — Runner updates plan status during execution

Security:
  - IDOR: all user endpoints verify brand belongs to caller via JWT user_id
  - Injection: brand_id validated as strict UUID; topic/angle fields char-capped
  - Items list capped at 10 (prevents runaway execution)
  - topic_focus in write payload capped at 500 chars (prompt injection mitigation)
"""

from __future__ import annotations

import hmac
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.deps import get_admin_client

logger = logging.getLogger("app.routers.content_planning")

router = APIRouter(tags=["content-planning"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ── Pipeline key auth (same pattern as pipeline_settings.py) ──────────────


def _require_pipeline_key(
    x_pipeline_key: str = Header(..., alias="X-Pipeline-Key"),
) -> None:
    if not settings.pipeline_secret_key:
        raise HTTPException(503, "Pipeline key not configured.")
    if not hmac.compare_digest(x_pipeline_key, settings.pipeline_secret_key):
        raise HTTPException(401, "Invalid pipeline key")


# ── Planning system prompts ───────────────────────────────────────────────

_BRAINSTORM_SYSTEM = """\
You are Jumbo, the strategic content partner for PositionedUp.

Your job is to open a content planning conversation. Help the user decide WHAT to create — not by deciding for them, but by surfacing opportunities and letting them choose.

Opening message structure (follow this exactly):
1. One sentence acknowledging their niche / brand focus
2. Present 3–5 content opportunities. For each one, give:
   - A specific topic title (not generic)
   - One-line WHY it matters (ICA alignment, competitor gap, or performance pattern)
3. Ask directly: how many posts do they want, and which topics appeal to them?

Style rules:
- Be a smart colleague, not a consultant writing a report
- Specific > generic (quote from their brand context)
- Conversational, direct, energetic
- DO NOT write any post content — only surface opportunities

Brand context injected below. Use it to make suggestions specific to THIS brand.

BRAND: {brand_name}
NICHE / ICA: {ica}
VOICE: {voice}
CONTENT PILLARS: {pillars}
RECENT TRENDS: {trend_ctx}
TOP PERFORMING POSTS: {analytics_ctx}
REJECTION HISTORY (avoid these): {rejection_history}
"""

_CHAT_SYSTEM = """\
You are Jumbo, the strategic content partner for PositionedUp. You are mid-conversation helping the user plan their content.

Continue the planning conversation naturally. When the user confirms what they want, summarise the agreed plan using EXACTLY this format at the end of your message:

PLAN:
- [topic title] | [angle or style] | [format: post/thread/carousel]
- [topic title] | [angle or style] | [format: post/thread/carousel]

Rules:
- Each line must use | as separator (not dash, not comma)
- Maximum 10 items
- Keep topic titles concise (under 60 chars)
- Only include the PLAN: section when the user has confirmed their choices — not during exploration
- Be warm, strategic, and specific. Reference their brand when relevant.
"""


# ── Schemas ───────────────────────────────────────────────────────────────


class BrainstormRequest(BaseModel):
    brand_id: str


class PlanChatRequest(BaseModel):
    brand_id: str
    messages: List[Dict[str, str]]  # [{role: "user"|"jumbo", content: str}]


class PlanItem(BaseModel):
    topic: str
    angle: str = ""
    format: str = "post"


class ApproveRequest(BaseModel):
    brand_id: str
    items: List[PlanItem]


class StatusUpdateRequest(BaseModel):
    status: str  # approved | executing | done | failed | partial
    item_results: Optional[List[Dict[str, str]]] = None  # [{topic, status}]


# ── IDOR helper ───────────────────────────────────────────────────────────


def _verify_brand_ownership(brand_id: str, user_id: str) -> None:
    """Raise 403 if brand does not belong to this user."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be a UUID")
    sb = get_admin_client()
    result = (
        sb.table("personal_brands")
        .select("id")
        .eq("id", brand_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(403, "Brand not found or access denied")


# ── User endpoints (JWT auth) ─────────────────────────────────────────────


@router.post("/plan/brainstorm")
async def brainstorm(
    body: BrainstormRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Jumbo opens the planning conversation with trending opportunities.

    Loads: trending topics, brand context, recent analytics, rejection history.
    Falls back to content pillars if no trend memory exists (new user).
    """
    from app.services.jumbo_pipeline import (
        get_analytics_context,
        get_brand_context,
        get_rejection_history,
        get_trend_memory,
    )
    from app.services.tool_use_agents import run_tool_use_agent

    _verify_brand_ownership(body.brand_id, user.id)

    brand_ctx = get_brand_context(body.brand_id) or {}
    brand_name = brand_ctx.get("name", "your brand")
    ica = brand_ctx.get("ica", "")
    voice = brand_ctx.get("voice", "")
    pillars = brand_ctx.get("content_pillars", [])

    trend_ctx = get_trend_memory(body.brand_id)
    analytics_ctx = get_analytics_context(body.brand_id)
    rejection_history = get_rejection_history(user.id, body.brand_id)

    # Fallback: no trend memory yet (new user) → seed from content pillars
    if not trend_ctx.strip() or "No previous trend research" in trend_ctx:
        if pillars:
            trend_ctx = "Based on brand pillars: " + ", ".join(str(p) for p in pillars[:5])
        else:
            trend_ctx = "No recent trend research — suggest based on brand ICA and voice."

    system_prompt = _BRAINSTORM_SYSTEM.format(
        brand_name=brand_name,
        ica=ica[:300] if ica else "not set",
        voice=voice[:200] if voice else "not set",
        pillars=", ".join(str(p) for p in pillars[:6]) if pillars else "not set",
        trend_ctx=trend_ctx[:1500],
        analytics_ctx=analytics_ctx[:1000],
        rejection_history=rejection_history[:500] if rejection_history else "none",
    )

    result = run_tool_use_agent(
        agent_id="jumbo",
        task_type="planning_brainstorm",
        system_prompt=system_prompt,
        user_prompt="Open the content planning conversation for this brand. Send your opening message.",
        user_id=user.id,
        brand_id=body.brand_id,
        available_tools=[],
        temperature=0.7,
    )

    if not result.success:
        logger.warning("brainstorm failed brand=%s: %s", body.brand_id, result.error)
        raise HTTPException(500, "Jumbo is unavailable right now — try again in a moment")

    return {"message": result.content, "brand_name": brand_name}


@router.post("/plan/chat")
async def plan_chat(
    body: PlanChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Continue the multi-turn planning conversation.

    Takes the full message history and returns Jumbo's next response.
    When the user confirms their choices, Jumbo ends with a PLAN: section
    that the frontend parses to show the Approve button.
    """
    from app.services.tool_use_agents import run_tool_use_agent

    _verify_brand_ownership(body.brand_id, user.id)

    if not body.messages:
        raise HTTPException(400, "messages cannot be empty")

    # Format last 10 messages as conversation history for the prompt
    recent = body.messages[-10:]
    history = "\n".join(
        f"{'USER' if m.get('role') == 'user' else 'JUMBO'}: {str(m.get('content', ''))[:800]}"
        for m in recent
    )

    result = run_tool_use_agent(
        agent_id="jumbo",
        task_type="planning_chat",
        system_prompt=_CHAT_SYSTEM,
        user_prompt=history,
        user_id=user.id,
        brand_id=body.brand_id,
        available_tools=[],
        temperature=0.7,
    )

    if not result.success:
        logger.warning("plan_chat failed brand=%s: %s", body.brand_id, result.error)
        raise HTTPException(500, "Jumbo is unavailable right now — try again in a moment")

    return {"response": result.content}


@router.post("/plan/approve")
async def approve_plan(
    body: ApproveRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Save the approved content plan to DB. VPS runner picks it up and executes it.

    Items capped at 10. Topic/angle text capped to prevent injection.
    """
    _verify_brand_ownership(body.brand_id, user.id)

    if not body.items:
        raise HTTPException(400, "items cannot be empty")

    # Sanitise and cap
    safe_items = [
        {
            "topic": item.topic[:300].strip(),
            "angle": item.angle[:200].strip(),
            "format": item.format[:50].strip() or "post",
        }
        for item in body.items[:10]
        if item.topic.strip()
    ]

    if not safe_items:
        raise HTTPException(400, "No valid items after sanitisation")

    now = datetime.now(timezone.utc)
    sb = get_admin_client()
    result = sb.table("content_plans").insert({
        "user_id": user.id,
        "brand_id": body.brand_id,
        "items": safe_items,
        "status": "approved",
        "approved_at": now.isoformat(),
        "last_updated_at": now.isoformat(),
    }).execute()

    if not result.data:
        raise HTTPException(500, "Failed to save plan")

    plan_id = result.data[0]["id"]
    logger.info("content_plan approved plan=%s user=%s items=%d", plan_id, user.id, len(safe_items))
    return {"plan_id": plan_id, "item_count": len(safe_items), "status": "approved"}


@router.get("/plan/status/{plan_id}")
async def plan_status(
    plan_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Poll plan execution status. Detects zombie 'executing' plans (>10 min stale)."""
    if not _UUID_RE.match(plan_id):
        raise HTTPException(400, "Invalid plan_id")

    sb = get_admin_client()
    result = (
        sb.table("content_plans")
        .select("*")
        .eq("id", plan_id)
        .eq("user_id", user.id)  # IDOR guard
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Plan not found")

    plan = result.data[0]
    status = plan.get("status", "unknown")

    # Zombie detection: executing for >30 min without update → treat as failed
    if status == "executing":
        last_updated = plan.get("last_updated_at")
        if last_updated:
            try:
                updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - updated_dt > timedelta(minutes=30):
                    status = "failed"
                    # Persist zombie → failed so future polls don't re-check
                    try:
                        sb.table("content_plans").update({
                            "status": "failed",
                            "last_updated_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", plan_id).execute()
                    except Exception as z_exc:
                        logger.warning("Failed to persist zombie status plan=%s: %s", plan_id, z_exc)
            except Exception:
                pass

    items = plan.get("items", [])
    items_done = sum(1 for i in items if i.get("status") == "done")
    items_failed = sum(1 for i in items if i.get("status") == "failed")
    return {
        "status": status,
        "item_count": len(items),
        "items_done": items_done,
        "items_failed": items_failed,
        "brand_id": plan.get("brand_id"),
    }


# ── VPS runner endpoints (pipeline-key auth) ──────────────────────────────


@router.get("/plan/approved-for-runner")
async def get_approved_plans(
    _key: None = Depends(_require_pipeline_key),
) -> Dict[str, Any]:
    """Return all content_plans with status='approved', ordered by approval time.

    Called by the VPS pipeline runner before each execution cycle.
    """
    try:
        sb = get_admin_client()

        # Auto-fail stale executing plans (>30 min without update)
        stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        try:
            sb.table("content_plans").update({
                "status": "failed",
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("status", "executing").lt("last_updated_at", stale_cutoff).execute()
        except Exception as stale_exc:
            logger.warning("stale plan cleanup failed: %s", stale_exc)

        result = (
            sb.table("content_plans")
            .select("*")
            .eq("status", "approved")
            .order("approved_at", desc=False)
            .execute()
        )
        return {"plans": result.data or []}
    except Exception as exc:
        logger.warning("get_approved_plans failed: %s", exc)
        return {"plans": []}


@router.patch("/plan/{plan_id}/status")
async def update_plan_status(
    plan_id: str,
    body: StatusUpdateRequest,
    _key: None = Depends(_require_pipeline_key),
) -> Dict[str, Any]:
    """VPS runner calls this to update plan status during/after execution.

    Valid transitions: approved → executing → done | failed
    """
    if not _UUID_RE.match(plan_id):
        raise HTTPException(400, "Invalid plan_id")

    valid_statuses = {"approved", "executing", "done", "failed", "partial"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    try:
        sb = get_admin_client()

        # Idempotency guard: only allow executing if plan is currently approved
        if body.status == "executing":
            current = (
                sb.table("content_plans")
                .select("status")
                .eq("id", plan_id)
                .limit(1)
                .execute()
            )
            if current.data and current.data[0].get("status") != "approved":
                return {"ok": False, "reason": "Plan is not in approved state"}

        update_data: Dict[str, Any] = {
            "status": body.status,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Merge per-item results into the items JSONB
        if body.item_results:
            plan_row = (
                sb.table("content_plans")
                .select("items")
                .eq("id", plan_id)
                .limit(1)
                .execute()
            )
            if plan_row.data:
                existing_items = plan_row.data[0].get("items", [])
                # Build lookup of results by topic
                result_map = {r["topic"]: r["status"] for r in body.item_results}
                for item in existing_items:
                    topic = item.get("topic", "")
                    if topic in result_map:
                        item["status"] = result_map[topic]
                update_data["items"] = existing_items

        sb.table("content_plans").update(update_data).eq("id", plan_id).execute()
        return {"ok": True, "plan_id": plan_id, "status": body.status}
    except Exception as exc:
        logger.warning("update_plan_status failed plan=%s: %s", plan_id, exc)
        return {"ok": False}
