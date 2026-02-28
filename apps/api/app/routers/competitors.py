"""Competitor Intelligence router.

Endpoints:
  - GET    /competitors                  -- List tracked competitors
  - POST   /competitors                  -- Add new competitor
  - GET    /competitors/comparison       -- Compare user vs competitor
  - GET    /competitors/gaps             -- Content gap analysis
  - GET    /competitors/intelligence     -- Intelligence feed (aggregated)
  - GET    /competitors/alerts           -- Recent competitor alerts
  - POST   /competitors/full-analysis    -- Trigger full analysis of all competitors
  - GET    /competitors/{id}             -- Get competitor detail
  - PATCH  /competitors/{id}             -- Update competitor
  - DELETE /competitors/{id}             -- Archive competitor
  - GET    /competitors/{id}/metrics     -- Historical metrics
  - POST   /competitors/{id}/metrics     -- Record new metric snapshot
  - GET    /competitors/{id}/content     -- Recent content
  - POST   /competitors/{id}/refresh     -- Scan URL for fresh data
  - POST   /competitors/{id}/analyze     -- LLM analysis report
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.competitors import (
    CompetitorAnalysisReport,
    CompetitorComparison,
    CompetitorContentOut,
    CompetitorContentRecord,
    CompetitorCreate,
    CompetitorMetricOut,
    CompetitorMetricRecord,
    CompetitorOut,
    CompetitorUpdate,
    ContentGapAnalysis,
    IntelligenceFeed,
)
from app.services import competitor_intel as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/competitors", tags=["competitors"])


# ── List / Create ───────────────────────────────────────────────


@router.get("", response_model=List[CompetitorOut])
async def list_competitors(
    brand_id: Optional[str] = Query(None),
    comp_status: str = Query("active", alias="status"),
    user: CurrentUser = Depends(get_current_user),
):
    """List tracked competitors, optionally filtered by brand."""
    admin = get_admin_client()
    return svc.list_competitors(user.id, admin, brand_id=brand_id, status=comp_status)


@router.post("", response_model=CompetitorOut, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    body: CompetitorCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Add a new competitor to track."""
    admin = get_admin_client()
    return svc.create_competitor(user.id, body.model_dump(), admin)


# ── Comparison & Gaps (before {id} routes to avoid path conflicts) ─


@router.get("/comparison", response_model=CompetitorComparison)
async def compare_competitor(
    competitor_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Compare your metrics with a competitor side-by-side."""
    admin = get_admin_client()
    result = svc.compare_with_user(user.id, competitor_id, admin)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get("/gaps", response_model=ContentGapAnalysis)
async def content_gaps(
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Identify content topics your competitors cover that you don't."""
    admin = get_admin_client()
    return svc.get_content_gap_analysis(user.id, admin, brand_id=brand_id)


# ── Intelligence Feed ─────────────────────────────────────────


@router.get("/intelligence", response_model=IntelligenceFeed)
async def intelligence_feed(
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Aggregated competitor intelligence feed: stats, analyses, alerts, benchmarks."""
    admin = get_admin_client()
    return svc.get_intelligence_feed(user.id, admin, brand_id=brand_id)


@router.get("/alerts")
async def competitor_alerts(
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Get recent competitor alerts from notifications."""
    admin = get_admin_client()
    try:
        resp = (
            admin.table("agent_notifications")
            .select("*")
            .eq("user_id", user.id)
            .ilike("action_url", "%/competitors%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("Failed to fetch competitor alerts: %s", e)
        return []


@router.post("/full-analysis")
async def trigger_full_analysis(
    brand_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Trigger LLM analysis for all active competitors (capped at 10)."""
    admin = get_admin_client()
    competitors = svc.list_competitors(user.id, admin, brand_id=brand_id)
    results = []
    for comp in competitors[:10]:
        try:
            report = svc.generate_analysis_report(user.id, comp["id"], admin)
            results.append({
                "competitor_id": comp["id"],
                "name": comp["name"],
                "status": "ok",
                "summary": (report.get("summary") or "")[:200],
            })
        except Exception as e:
            results.append({
                "competitor_id": comp["id"],
                "name": comp["name"],
                "status": "error",
                "error": str(e)[:200],
            })
    return {"analyzed": len(results), "results": results}


# ── Single competitor CRUD ──────────────────────────────────────


@router.get("/{competitor_id}", response_model=CompetitorOut)
async def get_competitor(
    competitor_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get competitor profile with metrics and recent content."""
    admin = get_admin_client()
    comp = svc.get_competitor(competitor_id, user.id, admin)
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return comp


@router.patch("/{competitor_id}", response_model=CompetitorOut)
async def update_competitor(
    competitor_id: str,
    body: CompetitorUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update competitor details."""
    admin = get_admin_client()
    comp = svc.update_competitor(competitor_id, user.id, body.model_dump(exclude_unset=True), admin)
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return comp


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Archive a competitor (soft delete)."""
    admin = get_admin_client()
    deleted = svc.delete_competitor(competitor_id, user.id, admin)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")


# ── Metrics ─────────────────────────────────────────────────────


@router.get("/{competitor_id}/metrics", response_model=List[CompetitorMetricOut])
async def get_metrics(
    competitor_id: str,
    days: int = Query(30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
):
    """Get historical metrics for a competitor."""
    admin = get_admin_client()
    # Verify ownership
    comp = svc.get_competitor(competitor_id, user.id, admin)
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return svc.get_metrics_history(competitor_id, admin, days=days)


@router.post("/{competitor_id}/metrics", response_model=CompetitorMetricOut, status_code=status.HTTP_201_CREATED)
async def record_metrics(
    competitor_id: str,
    body: CompetitorMetricRecord,
    user: CurrentUser = Depends(get_current_user),
):
    """Record a new metrics snapshot for a competitor."""
    admin = get_admin_client()
    comp = svc.get_competitor(competitor_id, user.id, admin)
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return svc.record_metrics(competitor_id, body.model_dump(), admin)


# ── Content ─────────────────────────────────────────────────────


@router.get("/{competitor_id}/content", response_model=List[CompetitorContentOut])
async def get_content(
    competitor_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    """Get recent tracked content for a competitor."""
    admin = get_admin_client()
    comp = svc.get_competitor(competitor_id, user.id, admin)
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    return svc.get_recent_content(competitor_id, admin, limit=limit)


# ── Refresh & Analyze ───────────────────────────────────────────


@router.post("/{competitor_id}/refresh")
async def refresh_competitor(
    competitor_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Scan competitor URL for fresh data and update records."""
    admin = get_admin_client()
    result = svc.refresh_competitor_data(competitor_id, user.id, admin)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.post("/{competitor_id}/analyze", response_model=CompetitorAnalysisReport)
async def analyze_competitor(
    competitor_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate an LLM-powered competitive analysis report."""
    admin = get_admin_client()
    result = svc.generate_analysis_report(user.id, competitor_id, admin)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result
