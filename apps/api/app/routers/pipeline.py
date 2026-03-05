"""Pipeline Router — Slice 89.

3-phase automated content pipeline, plus a Vercel publishing cron.

Endpoints:
  POST /orchestrator/pipeline/research  — Phase 1: trend research with context injection
  POST /orchestrator/pipeline/write     — Phase 2: write from research brief + analytics
  POST /orchestrator/pipeline/qa        — Phase 3: QA review, save deliverable, notify
  GET  /orchestrator/pipeline/status    — Recent pipeline runs from sdk_agent_runs
  POST /cron/publish                    — Vercel hourly cron: publish all due items

Authentication:
  Pipeline endpoints: X-Pipeline-Key header (shared secret, VPS ↔ Vercel API)
  Cron endpoint:      Authorization: Bearer <CRON_SECRET> (Vercel-injected)

Security:
  - Both auth mechanisms use hmac.compare_digest (timing-safe)
  - brand_id and user_id validated as strict UUIDs before any DB query (OWASP A03)
  - Cron secret validates Vercel cron authority (OWASP A01)
"""

from __future__ import annotations

import hmac
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.deps import get_admin_client
from app.services.jumbo_pipeline import (
    build_qa_prompt,
    build_research_prompt,
    build_writing_prompt,
    check_monthly_budget,
    get_analytics_context,
    get_competitor_context,
    get_rejection_history,
    get_relevant_experiences,
    get_trend_memory,
    mark_experiences_used,
    notify_approval_needed,
    parse_qa_score,
    save_deliverable,
    save_research_brief,
)
from app.services.tool_use_agents import run_tool_use_agent

logger = logging.getLogger("app.routers.pipeline")

router = APIRouter(tags=["pipeline"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# ── Auth dependencies ─────────────────────────────────────────────────────


def _require_pipeline_key(
    x_pipeline_key: str = Header(..., alias="X-Pipeline-Key"),
) -> None:
    """Validate the shared pipeline secret using constant-time comparison."""
    if not settings.pipeline_secret_key:
        raise HTTPException(
            503, "Pipeline key not configured. Set PIPELINE_SECRET_KEY in env."
        )
    if not hmac.compare_digest(x_pipeline_key, settings.pipeline_secret_key):
        raise HTTPException(401, "Invalid pipeline key")


def _require_cron_auth(
    authorization: Optional[str] = Header(None),
    x_pipeline_key: Optional[str] = Header(None, alias="X-Pipeline-Key"),
) -> None:
    """Accept either Vercel CRON_SECRET or the pipeline key.

    - Vercel cron sends: Authorization: Bearer <CRON_SECRET>
    - VPS runner sends:  X-Pipeline-Key: <PIPELINE_SECRET_KEY>
    In local dev (no secrets configured), auth is skipped.
    """
    # Accept pipeline key (VPS runner calling after each run)
    if x_pipeline_key and settings.pipeline_secret_key:
        if hmac.compare_digest(x_pipeline_key, settings.pipeline_secret_key):
            return

    # Accept Vercel cron secret
    if settings.cron_secret:
        if not authorization:
            raise HTTPException(401, "Missing auth for cron endpoint")
        expected = f"Bearer {settings.cron_secret}"
        if hmac.compare_digest(authorization, expected):
            return
        raise HTTPException(401, "Invalid cron secret")

    # Local dev — allow without auth
    if os.environ.get("VERCEL") == "1":
        raise HTTPException(503, "No cron auth configured on Vercel")
    return


def _validate_ids(brand_id: str, user_id: str) -> None:
    """Reject non-UUID brand_id / user_id to prevent SQL/path injection (OWASP A03)."""
    if not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be a UUID")
    if not _UUID_RE.match(user_id):
        raise HTTPException(400, "Invalid user_id — must be a UUID")


# ── Request / Response schemas ────────────────────────────────────────────


class ResearchRequest(BaseModel):
    brand_id: str
    user_id: str


class ResearchResponse(BaseModel):
    research_brief: str
    tokens: int = 0


class WriteRequest(BaseModel):
    brand_id: str
    user_id: str
    research_brief: str


class WriteResponse(BaseModel):
    draft: str
    self_qa_passed: bool = False


class QARequest(BaseModel):
    brand_id: str
    user_id: str
    draft: str


class QAResponse(BaseModel):
    qa_score: int
    verdict: str
    saved: bool
    deliverable_id: Optional[str] = None


# ── Phase 1: Research ─────────────────────────────────────────────────────


@router.post("/orchestrator/pipeline/research", response_model=ResearchResponse)
async def pipeline_research(
    req: ResearchRequest,
    _key: None = Depends(_require_pipeline_key),
):
    """Phase 1: Research trending topics with competitor + analytics context.

    Injects analytics context (what's worked before), competitor context
    (what to avoid repeating), and previous trend memory (topics already done).
    Calls run_tool_use_agent() with the trend-analyzer persona.
    """
    _validate_ids(req.brand_id, req.user_id)

    # Budget gate — check monthly spend before starting expensive LLM run
    budget_error = check_monthly_budget(req.user_id)
    if budget_error:
        raise HTTPException(429, budget_error)

    analytics_ctx = get_analytics_context(req.brand_id)
    competitor_ctx = get_competitor_context(req.brand_id)
    trend_memory = get_trend_memory(req.brand_id)

    system_prompt = build_research_prompt(analytics_ctx, competitor_ctx, trend_memory)
    user_prompt = (
        f"Research 3 trending content topics for brand_id={req.brand_id}. "
        f"Start by reading your playbook: call read_playbook with "
        f"agent_id='trend-analyzer' and user_id='{req.user_id}'. "
        "Then use web_search to find current trends. "
        "Synthesize into a structured research brief."
    )

    result = run_tool_use_agent(
        agent_id="trend-analyzer",
        task_type="pipeline_research",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=req.user_id,
        brand_id=req.brand_id,
        available_tools=["web_search", "synthesize_research", "read_playbook"],
    )

    if not result.success:
        logger.warning(
            "Research phase failed brand=%s: %s", req.brand_id, result.error
        )
        raise HTTPException(500, f"Research phase failed: {result.error}")

    # Persist research brief to DB so Sales agents can read it
    save_research_brief(
        user_id=req.user_id,
        brand_id=req.brand_id,
        content=result.content,
    )

    return ResearchResponse(research_brief=result.content, tokens=result.tokens_used)


# ── Phase 2: Write ────────────────────────────────────────────────────────


@router.post("/orchestrator/pipeline/write", response_model=WriteResponse)
async def pipeline_write(
    req: WriteRequest,
    _key: None = Depends(_require_pipeline_key),
):
    """Phase 2: Write a post using the research brief + analytics + rejection history.

    Injects: research brief, analytics context (hook/format patterns that worked),
    and rejection history (mistakes to avoid).
    """
    _validate_ids(req.brand_id, req.user_id)

    analytics_ctx = get_analytics_context(req.brand_id)
    rejection_history = get_rejection_history(req.user_id, req.brand_id)
    experiences_ctx, experience_ids = get_relevant_experiences(
        req.user_id, req.brand_id, topic=req.research_brief[:500]
    )

    system_prompt = build_writing_prompt(
        req.research_brief, analytics_ctx, rejection_history, experiences_ctx
    )
    user_prompt = (
        f"Write a LinkedIn post for brand_id={req.brand_id}. "
        f"First read your playbook: read_playbook(agent_id='copywriter', user_id='{req.user_id}'). "
        f"Then fetch_brand_profile(brand_id='{req.brand_id}'). "
        "Write the post. Then score_content_quality on your draft. "
        "Fix any issues, then output the final post text only."
    )

    result = run_tool_use_agent(
        agent_id="copywriter",
        task_type="pipeline_write",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=req.user_id,
        brand_id=req.brand_id,
        available_tools=["fetch_brand_profile", "read_playbook", "score_content_quality"],
    )

    if not result.success:
        logger.warning(
            "Write phase failed brand=%s: %s", req.brand_id, result.error
        )
        raise HTTPException(500, f"Write phase failed: {result.error}")

    # Track which journal entries were used so the agent rotates to fresh material next time
    mark_experiences_used(experience_ids)

    self_qa_passed = len(result.content.strip()) >= 50

    return WriteResponse(draft=result.content, self_qa_passed=self_qa_passed)


# ── Phase 3: QA ───────────────────────────────────────────────────────────


@router.post("/orchestrator/pipeline/qa", response_model=QAResponse)
async def pipeline_qa(
    req: QARequest,
    _key: None = Depends(_require_pipeline_key),
):
    """Phase 3: QA review — score, save deliverable, notify user if pass.

    score >= 80 → status=review + notification in Home Inbox
    score < 80  → status=failed_qa (logged, not surfaced)
    """
    _validate_ids(req.brand_id, req.user_id)

    system_prompt = build_qa_prompt()
    user_prompt = (
        f"Review this post for brand_id={req.brand_id}. "
        "Call score_content_quality first, then apply the full rubric. "
        "Output EXACTLY: SCORE/VERDICT/STRENGTHS/IMPROVEMENTS.\n\n"
        f"Post to review:\n{req.draft[:2000]}"
    )

    result = run_tool_use_agent(
        agent_id="qa-reviewer",
        task_type="pipeline_qa",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        user_id=req.user_id,
        brand_id=req.brand_id,
        available_tools=["score_content_quality"],
    )

    # Even on LLM failure, persist the draft so nothing is lost
    if not result.success:
        logger.warning("QA phase failed brand=%s: %s", req.brand_id, result.error)
        deliverable_id = save_deliverable(
            user_id=req.user_id,
            content=req.draft,
            qa_score=0,
            title="Pipeline post — QA failed",
        )
        return QAResponse(
            qa_score=0,
            verdict="FAIL",
            saved=bool(deliverable_id),
            deliverable_id=deliverable_id or None,
        )

    qa_score = parse_qa_score(result.content)
    verdict = "PASS" if qa_score >= 80 else "FAIL"

    deliverable_id = save_deliverable(
        user_id=req.user_id,
        content=req.draft,
        qa_score=qa_score,
        title=f"Pipeline post — QA {qa_score}/100",
    )

    if qa_score >= 80 and deliverable_id:
        notify_approval_needed(
            user_id=req.user_id,
            deliverable_id=deliverable_id,
            content_preview=req.draft,
        )

    logger.info(
        "QA complete brand=%s score=%d verdict=%s deliverable=%s",
        req.brand_id,
        qa_score,
        verdict,
        deliverable_id,
    )

    return QAResponse(
        qa_score=qa_score,
        verdict=verdict,
        saved=bool(deliverable_id),
        deliverable_id=deliverable_id or None,
    )


# ── Pipeline status ───────────────────────────────────────────────────────


@router.get("/orchestrator/pipeline/status")
async def pipeline_status(_key: None = Depends(_require_pipeline_key)):
    """Return the 15 most recent pipeline runs from sdk_agent_runs."""
    try:
        sb = get_admin_client()
        result = (
            sb.table("sdk_agent_runs")
            .select(
                "id, agent_id, task_type, status, total_tokens, "
                "duration_ms, created_at, brand_id"
            )
            .in_("task_type", ["pipeline_research", "pipeline_write", "pipeline_qa"])
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        return {"runs": result.data or []}
    except Exception as exc:
        logger.warning("pipeline_status query failed: %s", exc)
        return {"runs": [], "error": "Could not load status"}


# ── Active brands (for VPS pipeline runner) ───────────────────────────────


@router.get("/orchestrator/pipeline/brands")
async def pipeline_brands(_key: None = Depends(_require_pipeline_key)):
    """Return all active brands with user_id for the VPS pipeline runner.

    Authenticated with X-Pipeline-Key (server-to-server only).
    Returns list of {brand_id, user_id, name} for every active personal brand.
    """
    try:
        sb = get_admin_client()
        result = (
            sb.table("personal_brands")
            .select("id, name, user_id")
            .eq("is_active", True)
            .order("created_at", desc=False)
            .execute()
        )
        brands = [
            {"brand_id": row["id"], "user_id": row["user_id"], "name": row.get("name", "")}
            for row in (result.data or [])
            if row.get("id") and row.get("user_id")
        ]
        return {"brands": brands}
    except Exception as exc:
        logger.warning("pipeline_brands query failed: %s", exc)
        return {"brands": [], "error": "Could not load brands"}


# ── Publishing cron ───────────────────────────────────────────────────────


@router.post("/cron/publish")
async def cron_publish(_auth: None = Depends(_require_cron_auth)):
    """Vercel hourly cron: publish all scheduled items that are due.

    Processes every user who has items with status='scheduled' AND
    scheduled_at <= now(). Errors per-item don't stop other items.

    Called by Vercel cron at: 0 * * * * (every hour).
    Protected by Authorization: Bearer <CRON_SECRET>.
    """
    from app.services.publishing import run_due_posts

    try:
        sb = get_admin_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Find all user_ids with due items (avoids full-table scan)
        due_resp = (
            sb.table("scheduled_items")
            .select("user_id")
            .eq("status", "scheduled")
            .lte("scheduled_at", now_iso)
            .execute()
        )

        if not due_resp.data:
            return {"published": 0, "errors": 0, "users_processed": 0}

        user_ids = list({row["user_id"] for row in due_resp.data})

        total_published = 0
        total_errors = 0

        for uid in user_ids:
            run_result = run_due_posts(user_id=uid, sb=sb)
            total_published += run_result.published
            total_errors += run_result.failed

        logger.info(
            "cron_publish complete: published=%d errors=%d users=%d",
            total_published,
            total_errors,
            len(user_ids),
        )

        return {
            "published": total_published,
            "errors": total_errors,
            "users_processed": len(user_ids),
        }

    except Exception as exc:
        logger.error("cron_publish failed: %s", exc)
        raise HTTPException(500, f"Publish cron failed: {str(exc)[:200]}")
