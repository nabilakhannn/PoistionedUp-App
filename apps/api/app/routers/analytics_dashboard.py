"""Analytics Dashboard Router — Slice 112.

Single endpoint returning all dashboard metrics in one call.

  GET /analytics/dashboard?brand_id=...&period=30d

Security: A01 IDOR (user_id filter), A03 UUID validation, A07 JWT auth.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user

logger = logging.getLogger("app.routers.analytics_dashboard")

router = APIRouter(tags=["analytics-dashboard"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_VALID_PERIODS = {"7d", "30d", "90d"}
_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}


# ── Response models ──────────────────────────────────────────────────────


class ContentROI(BaseModel):
    posts_per_day: float
    approval_rate: float
    avg_qa_score: float
    total_generated: int
    approved: int
    rejected: int
    in_review: int
    daily_breakdown: list


class PipelinePerformance(BaseModel):
    total_runs: int
    completed: int
    failed: int
    success_rate: float
    avg_duration_ms: int
    phase_breakdown: dict
    daily_runs: list


class RevenueAttribution(BaseModel):
    total_closed_won: float
    total_proposals_sent: int
    proposal_funnel: dict
    win_rate: float


class EngagementTrends(BaseModel):
    avg_engagement_rate: float
    total_views: int
    total_likes: int
    total_comments: int
    tier_distribution: dict
    top_posts: list
    hook_type_performance: list
    topic_performance: list
    best_posting_days: list


class LeadFunnel(BaseModel):
    total_leads: int
    status_distribution: dict
    bant_distribution: dict
    conversion_rate: float
    new_leads_period: int


class CostTracking(BaseModel):
    total_tokens: int
    estimated_cost: float
    monthly_budget: float
    budget_utilization: float
    cost_per_content: float
    daily_spend: list


class AnalyticsDashboardResponse(BaseModel):
    period: str
    period_start: str
    period_end: str
    content_roi: ContentROI
    pipeline: PipelinePerformance
    revenue: RevenueAttribution
    engagement: EngagementTrends
    leads: LeadFunnel
    cost: CostTracking


# ── Data fetchers (run in threads) ───────────────────────────────────────


def _fetch_deliverables(user_id: str, brand_id: Optional[str], cutoff: str):
    from app.deps import get_admin_client

    sb = get_admin_client()
    q = (
        sb.table("agent_deliverables")
        .select("status, qa_score, created_at, proposal_status, deal_value, client_brand, brand_id")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
    )
    if brand_id:
        q = q.eq("brand_id", brand_id)
    return q.limit(5000).execute().data or []


def _fetch_runs(user_id: str, brand_id: Optional[str], cutoff: str):
    from app.deps import get_admin_client

    sb = get_admin_client()
    q = (
        sb.table("sdk_agent_runs")
        .select("task_type, status, duration_ms, total_tokens, created_at")
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
    )
    if brand_id:
        q = q.eq("brand_id", brand_id)
    return q.limit(5000).execute().data or []


def _fetch_posts(user_id: str, brand_id: Optional[str], cutoff: str):
    from app.deps import get_admin_client

    sb = get_admin_client()
    q = (
        sb.table("content_posts")
        .select(
            "engagement_rate, performance_tier, hook_type, topic_category, "
            "day_of_week, views, likes, comments, shares, saves, title, "
            "platform, published_at, created_at"
        )
        .eq("user_id", user_id)
        .gte("created_at", cutoff)
    )
    if brand_id:
        q = q.eq("brand_id", brand_id)
    return q.limit(5000).execute().data or []


def _fetch_leads(user_id: str, brand_id: Optional[str]):
    from app.deps import get_admin_client

    sb = get_admin_client()
    q = (
        sb.table("leads")
        .select("status, bant_score, created_at")
        .eq("user_id", user_id)
    )
    if brand_id:
        q = q.eq("brand_id", brand_id)
    return q.limit(5000).execute().data or []


def _fetch_budget(user_id: str):
    from app.deps import get_admin_client

    sb = get_admin_client()
    result = (
        sb.table("pipeline_settings")
        .select("monthly_budget_usd")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return float(result.data[0].get("monthly_budget_usd") or 20.0)
    return 20.0


# ── Main endpoint ────────────────────────────────────────────────────────


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardResponse)
async def analytics_dashboard(
    brand_id: Optional[str] = Query(default=None),
    period: str = Query(default="30d"),
    user: CurrentUser = Depends(get_current_user),
):
    """Return comprehensive analytics dashboard data."""
    if brand_id and not _UUID_RE.match(brand_id):
        raise HTTPException(400, "Invalid brand_id — must be UUID")
    if period not in _VALID_PERIODS:
        raise HTTPException(400, f"Invalid period. Must be one of: {sorted(_VALID_PERIODS)}")

    period_days = _PERIOD_DAYS[period]
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=period_days)).isoformat()
    period_start = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")
    period_end = now.strftime("%Y-%m-%d")

    # Fetch all data in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_fetch_deliverables, user.id, brand_id, cutoff): "deliverables",
            executor.submit(_fetch_runs, user.id, brand_id, cutoff): "runs",
            executor.submit(_fetch_posts, user.id, brand_id, cutoff): "posts",
            executor.submit(_fetch_leads, user.id, brand_id): "leads",
            executor.submit(_fetch_budget, user.id): "budget",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                logger.warning("analytics fetch %s failed: %s", key, exc)
                results[key] = [] if key != "budget" else 20.0

    deliverables = results.get("deliverables", [])
    runs = results.get("runs", [])
    posts = results.get("posts", [])
    leads = results.get("leads", [])
    budget = results.get("budget", 20.0)

    # Compute all sections
    from app.services.analytics_dashboard import (
        compute_content_roi,
        compute_cost_tracking,
        compute_engagement_trends,
        compute_lead_funnel,
        compute_pipeline_performance,
        compute_revenue_attribution,
    )

    content_roi = compute_content_roi(deliverables, period_days)
    pipeline = compute_pipeline_performance(runs)
    revenue = compute_revenue_attribution(deliverables)
    engagement = compute_engagement_trends(posts)
    lead_funnel = compute_lead_funnel(leads, period_start=period_start)
    cost = compute_cost_tracking(runs, budget, content_roi["total_generated"])

    return AnalyticsDashboardResponse(
        period=period,
        period_start=period_start,
        period_end=period_end,
        content_roi=ContentROI(**content_roi),
        pipeline=PipelinePerformance(**pipeline),
        revenue=RevenueAttribution(**revenue),
        engagement=EngagementTrends(**engagement),
        leads=LeadFunnel(**lead_funnel),
        cost=CostTracking(**cost),
    )
